/** Authenticated loopback bridge. Received text is data, never a desktop command. */
import { randomUUID, createHash, timingSafeEqual } from 'node:crypto';
import { DatabaseSync } from 'node:sqlite';
import { mkdirSync, chmodSync } from 'node:fs';
import path from 'node:path';
import { validText } from '../portfolio/client.js';

const TTL = 300000;
export function openSendLedger(directory) {
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const filename = path.join(directory, 'desktop-sends.sqlite');
  const db = new DatabaseSync(filename);
  try {
    chmodSync(filename, 0o600);
    db.exec(`PRAGMA busy_timeout=1000;
      CREATE TABLE IF NOT EXISTS sends (id TEXT PRIMARY KEY, digest TEXT NOT NULL, status TEXT NOT NULL);`);
    return {
      get: id => db.prepare('SELECT digest,status FROM sends WHERE id=?').get(id),
      start: (id, digest) => {
        if (db.prepare('SELECT count(*) AS n FROM sends').get().n >= 10000) throw new Error('ledger_full');
        db.prepare("INSERT INTO sends(id,digest,status) VALUES(?,?,'pending')").run(id, digest);
      },
      finish: (id, status) => db.prepare('UPDATE sends SET status=? WHERE id=?').run(status, id),
      close: () => db.close(),
    };
  } catch (error) { db.close(); throw error; }
}

export function createDesktopControl({ token = '', contacts, ledger, now = Date.now }) {
  const boot = randomUUID();
  let sequence = 0;
  let events = [];
  const seen = new Map();
  let active = false;
  let pending;
  let closed = false;
  let attempts = [];
  const enabled = /^[a-f0-9]{64}$/.test(token);
  function notify(incoming, displayName = '') {
    if (closed || !enabled || !validText(incoming?.text, 2000) || !contacts.has(incoming.chatId?.split('@')[0]) ||
        typeof incoming.id !== 'string' || !Number.isFinite(incoming.timestamp) || Math.abs(now() - incoming.timestamp) > TTL) return;
    for (const [key, expires] of seen) if (expires <= now()) seen.delete(key);
    const id = `${incoming.chatId}:${incoming.id}`;
    if (seen.has(id)) return;
    seen.set(id, now() + TTL);
    if (seen.size > 10000) seen.delete(seen.keys().next().value);
    const name = typeof displayName === 'string' ? displayName.replace(/[\p{Cc}\p{Cf}\p{Cs}]/gu, '').trim().slice(0, 80) : '';
    events.push({ sequence: ++sequence, sender: incoming.chatId.split('@')[0], name,
      text: incoming.text, timestamp: incoming.timestamp });
    events = events.filter(event => now() - event.timestamp <= TTL).slice(-100);
  }
  const json = (response, code, body) => {
    if (response.destroyed || response.writableEnded) return;
    response.writeHead(code, { 'content-type': 'application/json', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff' });
    response.end(JSON.stringify(body));
  };
  async function handle(request, response, bot) {
    if (!request.url?.startsWith('/control/')) return false;
    if (closed) { request.resume(); json(response, 503, { error: 'unavailable' }); return true; }
    const remote = request.socket.remoteAddress;
    const authorization = request.headers.authorization;
    const expected = Buffer.from(`Bearer ${token}`);
    const supplied = Buffer.from(typeof authorization === 'string' ? authorization : '');
    if (!enabled || !['127.0.0.1', '::1', '::ffff:127.0.0.1'].includes(remote) || request.headers.origin ||
        supplied.length !== expected.length || !timingSafeEqual(supplied, expected)) {
      request.resume(); json(response, 403, { error: 'forbidden' }); return true;
    }
    if (request.method === 'GET' && request.url === '/control/inbox') {
      events = events.filter(event => now() - event.timestamp <= TTL);
      json(response, 200, { events: events.slice(-20), partial: events.length > 20 });
      return true;
    }
    if (request.method === 'GET' && request.url.startsWith('/control/events')) {
      const url = new URL(request.url, 'http://localhost');
      if (url.pathname !== '/control/events') { json(response, 404, { error: 'not_found' }); return true; }
      const cursor = url.searchParams.get('after');
      const match = typeof cursor === 'string' ? cursor.match(/^([a-f0-9-]{36}):(\d{1,12})$/) : null;
      if (cursor && !match) { json(response, 400, { error: 'invalid_cursor' }); return true; }
      events = events.filter(event => now() - event.timestamp <= TTL);
      const after = match && match[1] === boot ? Number(match[2]) : sequence;
      const missed = Boolean(match && (match[1] !== boot || after > sequence ||
        (events.length ? after < events[0].sequence - 1 : after < sequence)));
      const selected = events.filter(event => event.sequence > after).slice(0, 20);
      const next = selected.length ? selected.at(-1).sequence : sequence;
      json(response, 200, { cursor: `${boot}:${next}`, missed, events: selected });
      return true;
    }
    if (request.method !== 'POST' || request.url !== '/control/send') {
      request.resume(); json(response, 404, { error: 'not_found' }); return true;
    }
    if (request.headers['content-type']?.split(';')[0].trim() !== 'application/json') {
      request.resume(); json(response, 415, { error: 'invalid_input' }); return true;
    }
    let body;
    try {
      const chunks = []; let size = 0;
      for await (const chunk of request) {
        size += chunk.length;
        if (size > 8192) { json(response, 413, { error: 'too_large' }); return true; }
        chunks.push(chunk);
      }
      body = JSON.parse(Buffer.concat(chunks).toString('utf8'));
    } catch { json(response, 400, { error: 'invalid_input' }); return true; }
    if (closed) { json(response, 503, { error: 'unavailable' }); return true; }
    if (!body || Object.keys(body).sort().join(',') !== 'recipient,request_id,text' ||
        !/^[a-f0-9]{8}-[a-f0-9]{4}-4[a-f0-9]{3}-[89ab][a-f0-9]{3}-[a-f0-9]{12}$/.test(body.request_id) ||
        !/^\d{8,15}$/.test(body.recipient) || !validText(body.text, 2000)) {
      json(response, 400, { error: 'invalid_input' }); return true;
    }
    if (!contacts.has(body.recipient)) { json(response, 403, { error: 'recipient_not_allowed' }); return true; }
    const digest = createHash('sha256').update(JSON.stringify([body.recipient, body.text])).digest('hex');
    const prior = ledger.get(body.request_id);
    if (prior) {
      json(response, prior.digest !== digest ? 409 : prior.status === 'sent' ? 200 : 202,
        prior.digest !== digest ? { error: 'id_conflict' } : { request_id: body.request_id, status: prior.status === 'sent' ? 'accepted' : 'unknown' });
      return true;
    }
    attempts = attempts.filter(at => now() - at < 60000);
    if (active || attempts.length >= 5) { json(response, 429, { error: 'busy' }); return true; }
    if (bot.status() !== 'connected') { json(response, 503, { error: 'not_connected' }); return true; }
    attempts.push(now());
    ledger.start(body.request_id, digest);
    active = true;
    let status = 'unknown';
    try { pending = Promise.resolve().then(() => bot.sendExplicit(body.recipient, body.text)); await pending; status = 'sent'; }
    catch { /* A network failure can occur after transmission. Never retry automatically. */ }
    finally { active = false; }
    try { ledger.finish(body.request_id, status); }
    catch { status = 'unknown'; } // Keep the prior pending receipt; never invite an unsafe retry.
    json(response, status === 'sent' ? 200 : 202, { request_id: body.request_id, status: status === 'sent' ? 'accepted' : 'unknown' });
    return true;
  }
  return { notify, handle, enabled,
    close: () => { closed = true; events = []; seen.clear(); },
    drain: async () => { await pending?.catch(() => {}); },
  };
}
