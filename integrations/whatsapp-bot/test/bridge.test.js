import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Conversation, TRIGGERS } from '../src/conversation.js';
import { createPortfolioClient, PortfolioError } from '../src/portfolio-client.js';
import { readConfig, DEFAULT_API } from '../src/config.js';
import { readIncoming } from '../src/incoming.js';

test('configuration refuses an unrestricted WhatsApp startup and unsafe API URLs', () => {
  assert.throws(() => readConfig({}), /TEST_CONTACTS/);
  assert.equal(readConfig({}, { requireContacts: false }).apiUrl, DEFAULT_API);
  for (const url of ['http://example.com/api/v1/chat/', 'https://user:secret@example.com/api/v1/chat/', 'https://example.com/admin/']) {
    assert.throws(() => readConfig({ PORTFOLIO_API_URL: url }, { requireContacts: false }));
  }
  assert.equal(readConfig({ PORTFOLIO_API_URL: 'http://127.0.0.1:8000/api/v1/chat/' }, { requireContacts: false }).port, 3000);
});

test('HTTP contract sends only message, bounded history and language; no WhatsApp identifiers', async () => {
  let sent;
  const answer = createPortfolioClient({ apiUrl: DEFAULT_API, timeoutMs: 1000, fetchImpl: async (url, options) => {
    sent = { url, options };
    return Response.json({ respuesta: 'Soy Aubar.' });
  } });
  assert.equal(await answer('Hello', [], 'en'), 'Soy Aubar.');
  assert.equal(sent.url, DEFAULT_API);
  assert.deepEqual(JSON.parse(sent.options.body), { mensaje: 'Hello', historial: [], idioma: 'en' });
  assert.equal(sent.options.redirect, 'error');
  assert.equal(sent.options.headers.authorization, undefined);
  assert.equal(sent.options.headers.origin, undefined);
});

test('client handles Render failures and refuses oversized or invalid responses without leaking bodies', async () => {
  for (const [response, code] of [
    [new Response('private', { status: 503 }), 'unavailable'],
    [Response.json({}, { status: 429, headers: { 'Retry-After': '60' } }), 'busy'],
    [Response.json({ respuesta: '' }), 'invalid_response'],
    [Response.json({ respuesta: 'x'.repeat(4001) }), 'invalid_response'],
    [new Response('x'.repeat(66000), { headers: { 'content-type': 'application/json' } }), 'invalid_response'],
  ]) {
    const answer = createPortfolioClient({ apiUrl: DEFAULT_API, timeoutMs: 1000, fetchImpl: async () => response });
    await assert.rejects(answer('hola'), error => error instanceof PortfolioError && error.code === code && !error.message.includes('private'));
  }
  const answer = createPortfolioClient({ apiUrl: DEFAULT_API, timeoutMs: 1000, fetchImpl: async () => { throw new DOMException('private', 'TimeoutError'); } });
  await assert.rejects(answer('hola'), { code: 'timeout' });
  await assert.rejects(answer('x'.repeat(1201)), { code: 'invalid_input' });
});

test('shutting down cancels an outstanding Render request instead of waiting for its timeout', async () => {
  const answer = createPortfolioClient({ apiUrl: DEFAULT_API, timeoutMs: 90000,
    fetchImpl: async (_url, { signal }) => new Promise((_resolve, reject) => {
      signal.addEventListener('abort', () => reject(signal.reason), { once: true });
    }),
  });
  const pending = answer('hola');
  answer.close();
  await assert.rejects(pending, { code: 'timeout' });
});

test('only opt-in activates Aubar, English is preserved, history is isolated and opt-out works', async () => {
  const calls = [];
  let clock = 1000000;
  let id = 0;
  const bot = new Conversation({ now: () => clock, answer: async (...args) => { calls.push(args); return 'A public portfolio answer.'; } });
  const send = (chatId, text) => bot.handle({ chatId, text, id: String(++id) });
  assert.equal(await send('a', 'hola'), null);
  assert.match(await send('a', [...TRIGGERS.keys()][0]), /Aubar/);
  await send('a', '¿Qué proyectos tiene?');
  await send('b', '/aubar en');
  await send('b', 'What skills?');
  assert.equal(calls[1][2], 'en');
  assert.equal(calls[1][1][0].content, '/aubar en');
  assert.match(calls[1][1][1].content, /I'm Aubar/);
  clock += 61000;
  await send('a', '¿Y Angular?');
  assert.equal(calls[2][1].length, 4);
  assert.match(await send('a', 'HUMANO'), /desactivado/);
  assert.equal(await send('a', 'otra pregunta'), null);
  clock += 31 * 60000;
  assert.equal(await send('b', 'And now?'), null);
});

test('follow-ups and reactivation preserve earlier questions, answers and the initial welcome', async () => {
  const calls = [];
  let id = 0;
  const bot = new Conversation({ answer: async (...args) => { calls.push(args); return 'El proyecto usa Angular.'; } });
  const send = text => bot.handle({ chatId: 'visitor', id: String(++id), text });
  const welcome = await send('/aubar');
  await send('Soy Juan, contame del proyecto del clima');
  assert.deepEqual(calls[0][1], [
    { role: 'user', content: '/aubar' }, { role: 'assistant', content: welcome },
  ]);
  await send('/aubar en');
  await send('And what framework does it use?');
  assert.equal(calls[1][2], 'en');
  assert.ok(calls[1][1].some(item => item.content.includes('Soy Juan')));
  assert.ok(calls[1][1].some(item => item.content === 'El proyecto usa Angular.'));
  assert.ok(calls[1][1].some(item => item.content === welcome));
});

test('duplicates, old messages, rate limits and API cooldown do not flood Render', async () => {
  let calls = 0;
  let clock = 1000000;
  const bot = new Conversation({ now: () => clock, answer: async () => { calls++; throw new PortfolioError('busy', 60000); } });
  const activation = { chatId: 'a', id: 'start', text: '/aubar' };
  await bot.handle(activation);
  assert.equal(await bot.handle(activation), null);
  assert.equal(await bot.handle({ ...activation, id: 'old', timestamp: clock - 300001 }), null);
  await bot.handle({ chatId: 'a', id: '1', text: 'pregunta' });
  await bot.handle({ chatId: 'a', id: '2', text: 'otra' });
  assert.equal(calls, 1);
  await bot.handle({ chatId: 'a', id: '3', text: 'otra' });
  await bot.handle({ chatId: 'a', id: '4', text: 'otra' });
  assert.equal(await bot.handle({ chatId: 'a', id: '5', text: 'otra' }), null);
});

test('history stays within the backend budget and opt-out discards an in-flight reply', async () => {
  let clock = 1000000;
  let id = 0;
  const bot = new Conversation({ now: () => clock, answer: async () => 'x'.repeat(4000) });
  const send = text => bot.handle({ chatId: 'a', id: String(++id), text });
  await send('/aubar');
  for (let i = 0; i < 12; i++) { clock += 61000; await send('y'.repeat(1200)); }
  const history = bot.sessions.get('a').history;
  assert.ok(history.length <= 8);
  assert.ok(history.reduce((sum, item) => sum + item.content.length, 0) <= 6000);
  let finish;
  bot.answer = () => new Promise(resolve => { finish = resolve; });
  clock += 61000;
  const pending = send('una pregunta');
  await send('STOP');
  finish('Respuesta que ya no debe enviarse.');
  assert.equal(await pending, null);
});

test('only explicitly allowed private contacts pass, including LID resolution', async () => {
  const contacts = new Set(['12345678901']);
  const message = { key: { remoteJid: '12345678901@s.whatsapp.net', id: 'one' }, message: { conversation: '/aubar' }, messageTimestamp: 1000 };
  assert.equal((await readIncoming(message, contacts)).chatId, '12345678901@s.whatsapp.net');
  for (const remoteJid of ['123@g.us', 'status@broadcast', '123@newsletter', '98765432101@s.whatsapp.net']) {
    assert.equal(await readIncoming({ ...message, key: { ...message.key, remoteJid } }, contacts), null);
  }
  assert.equal(await readIncoming({ ...message, key: { ...message.key, fromMe: true } }, contacts), null);
  const lid = { ...message, key: { ...message.key, remoteJid: '999@lid' } };
  assert.equal(await readIncoming(lid, contacts), null);
  assert.equal((await readIncoming(lid, contacts, async () => '12345678901@s.whatsapp.net')).replyJid, '999@lid');
});
