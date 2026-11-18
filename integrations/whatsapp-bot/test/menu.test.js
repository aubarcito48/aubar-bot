import { test } from 'node:test';
import assert from 'node:assert/strict';
import { Conversation } from '../src/conversation.js';

function fixture() {
  let clock = Date.now();
  let id = 0;
  const calls = [];
  const bot = new Conversation({ now: () => clock, answer: async (...args) => {
    calls.push(args);
    return 'Información publicada de la sección solicitada.';
  } });
  return { calls, send: text => {
    clock += 61000;
    return bot.handle({ chatId: 'visitor', id: String(++id), text, timestamp: clock });
  } };
}

test('initial menu covers every portfolio section and numbers become grounded queries', async () => {
  const { calls, send } = fixture();
  const welcome = await send('/aubar');
  const sections = ['Sobre Nahuel', 'Proyectos', 'Experiencia', 'Educación', 'Tecnologías', 'Contacto'];
  sections.forEach((section, index) => assert.ok(welcome.includes(`${index + 1}. ${section}`)));
  assert.equal(calls.length, 0);
  const intents = [/perfil/, /proyectos/, /experiencia laboral/, /educación/, /tecnologías/, /contactar/];
  for (let index = 0; index < intents.length; index++) {
    const reply = await send(String(index + 1));
    assert.match(calls[index][0], intents[index]);
    assert.equal(calls[index][2], 'es');
    assert.equal(reply, 'Información publicada de la sección solicitada.');
  }
});

test('menu reopens only on request and preserves context for free-form follow-ups', async () => {
  const { calls, send } = fixture();
  await send('/aubar');
  await send('Proyectos');
  assert.match(calls[0][0], /proyectos publicados/);
  const reactivation = await send('/aubar');
  assert.doesNotMatch(reactivation, /1\. Sobre Nahuel|Soy Aubar/);
  const menu = await send('MENÚ');
  assert.match(menu, /1\. Sobre Nahuel/);
  assert.doesNotMatch(menu, /Soy Aubar/);
  assert.equal(calls.length, 1);
  await send('¿Y ese proyecto usa Angular?');
  assert.equal(calls[1][0], '¿Y ese proyecto usa Angular?');
  assert.ok(calls[1][1].some(item => /proyectos publicados/.test(item.content)));
  assert.ok(calls[1][1].some(item => item.content === 'Información publicada de la sección solicitada.'));
});

test('English menu and accented section names work without activating opted-out contacts', async () => {
  const { calls, send } = fixture();
  assert.equal(await send('MENU'), null);
  assert.match(await send('/aubar en'), /4\. Education/);
  await send('Education');
  assert.match(calls[0][0], /education and training/);
  assert.equal(calls[0][2], 'en');
  await send('/aubar');
  await send('TECNOLOGIAS');
  assert.match(calls[1][0], /tecnologías/);
  await send('SALIR');
  assert.equal(await send('2'), null);
  assert.equal(await send('/menu'), null);
  assert.equal(calls.length, 2);
});
