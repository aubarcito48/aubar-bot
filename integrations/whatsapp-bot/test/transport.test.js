import { test } from 'node:test';
import assert from 'node:assert/strict';
import { EventEmitter } from 'node:events';
import { createWhatsApp } from '../src/whatsapp.js';
import { Conversation } from '../src/conversation.js';

test('transport filters history and contacts, does not leak QR, and cancels replies on opt-out', async () => {
  const events = new EventEmitter();
  const sent = [];
  const logs = [];
  let socketOptions;
  let ended = false;
  let finish;
  let started;
  const inFlight = new Promise(resolve => { started = resolve; });
  const conversation = new Conversation({ answer: () => new Promise(resolve => { finish = resolve; started(); }) });
  const fake = {
    ev: events, sendMessage: async (...args) => { sent.push(args); },
    end: () => { ended = true; },
    signalRepository: { lidMapping: { getPNForLID: async () => null } },
  };
  const bot = createWhatsApp({
    config: { contacts: new Set(['12345678901']), showQr: false },
    auth: { state: { creds: {}, keys: { get: async () => ({}), set: async () => {} } }, saveCreds: () => {} },
    conversation, log: value => logs.push(value),
    socketFactory: options => { socketOptions = options; return fake; },
  });
  const message = (id, text, jid = '12345678901@s.whatsapp.net') => ({
    key: { remoteJid: jid, id }, message: { conversation: text }, messageTimestamp: Math.floor(Date.now() / 1000),
  });
  const dispatch = async (messages, type = 'notify') => {
    events.emit('messages.upsert', { type, messages });
    await new Promise(resolve => setImmediate(resolve));
  };
  try {
    bot.start();
    assert.equal(socketOptions.syncFullHistory, false);
    events.emit('connection.update', { qr: 'PRIVATE-QR-TOKEN' });
    assert.ok(logs.every(value => !value.includes('PRIVATE-QR-TOKEN')));
    events.emit('connection.update', { connection: 'open' });
    await dispatch([message('old', '/aubar')], 'append');
    await dispatch([message('group', '/aubar', '1@g.us'), message('other', '/aubar', '98765432101@s.whatsapp.net')]);
    await bot.drain();
    assert.equal(sent.length, 0);
    await dispatch([message('start', '/aubar')]);
    await bot.drain();
    assert.equal(sent.length, 1);
    await dispatch([message('question', '¿Qué proyectos hizo?')]);
    await inFlight;
    await dispatch([message('stop', 'SALIR')]);
    finish('Esta respuesta ya no debe enviarse.');
    await bot.drain();
    assert.equal(sent.length, 2);
    assert.match(sent[1][1].text, /desactivado/);
    assert.equal(bot.status(), 'connected');
  } finally { bot.stop(); await bot.drain(); }
  assert.equal(ended, true);
});

test('transport sends card images with captions and falls back to text on media failure', async () => {
  const events = new EventEmitter();
  const sent = [];
  const image = Buffer.from('synthetic PNG');
  let active = true;
  const bot = createWhatsApp({
    config: { contacts: new Set(['12345678901']), showQr: false },
    auth: { state: { creds: {}, keys: { get: async () => ({}), set: async () => {} } }, saveCreds: () => {} },
    conversation: { clear: () => { active = false; }, handle: async () => ({ isCurrent: () => active,
      messages: [{ image, caption: 'Technologies', fallbackText: 'Frontend: Angular' }, { image, caption: 'GitHub statistics' }],
    }) },
    log: () => {},
    socketFactory: () => ({ ev: events, end: () => {},
      signalRepository: { lidMapping: { getPNForLID: async () => null } },
      sendMessage: async (_jid, content) => {
        if (content.caption === 'Technologies') throw new Error('simulated upload failure');
        sent.push(content);
      },
    }),
  });
  try {
    bot.start();
    events.emit('connection.update', { connection: 'open' });
    events.emit('messages.upsert', { type: 'notify', messages: [{
      key: { remoteJid: '12345678901@s.whatsapp.net', id: 'card-selection' },
      message: { conversation: '5' }, messageTimestamp: Math.floor(Date.now() / 1000),
    }] });
    await new Promise(resolve => setImmediate(resolve));
    await bot.drain();
    assert.deepEqual(sent[0], { text: 'Frontend: Angular' });
    assert.deepEqual(sent[1], { image, caption: 'GitHub statistics' });
    assert.ok(sent.every(content => !('fallbackText' in content)));
  } finally { bot.stop(); await bot.drain(); }
});

test('explicit desktop sends preserve text and notifications do not activate the conversation', async () => {
  const events = new EventEmitter(); const sent = []; const notices = [];
  const bot = createWhatsApp({
    config: { contacts: new Set(['12345678901']), showQr: false },
    auth: { state: { creds: {}, keys: { get: async () => ({}), set: async () => {} } }, saveCreds: () => {} },
    conversation: { clear: () => {}, handle: async () => null }, log: () => {},
    onIncoming: (...args) => notices.push(args),
    socketFactory: () => ({ ev: events, end: () => {},
      sendMessage: async (...args) => { sent.push(args); return { key: { id: 'ack' } }; },
      signalRepository: { lidMapping: { getPNForLID: async () => null } } }),
  });
  try {
    bot.start(); events.emit('connection.update', { connection: 'open' });
    await bot.sendExplicit('12345678901', 'Texto exacto.');
    assert.deepEqual(sent, [['12345678901@s.whatsapp.net', { text: 'Texto exacto.' }]]);
    await assert.rejects(bot.sendExplicit('98765432101', 'Not allowed'));
    events.emit('messages.upsert', { type: 'notify', messages: [{
      key: { remoteJid: '12345678901@s.whatsapp.net', id: 'new' }, pushName: 'Contacto',
      message: { conversation: 'Mensaje normal sin /aubar' }, messageTimestamp: Math.floor(Date.now() / 1000),
    }] });
    await new Promise(resolve => setImmediate(resolve)); await bot.drain();
    assert.equal(notices.length, 1);
    assert.equal(sent.length, 1);
  } finally { bot.stop(); await bot.drain(); }
});
