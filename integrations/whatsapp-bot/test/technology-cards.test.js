import { test } from 'node:test';
import assert from 'node:assert/strict';
import sharp from 'sharp';
import { createTechnologyCards, staticSvg } from '../src/technology-cards.js';
import { Conversation } from '../src/conversation.js';

const svg = '<svg xmlns="http://www.w3.org/2000/svg" width="200" height="60"><rect width="200" height="60" fill="#112233"/><text x="10" y="30">Public data</text></svg>';
function sources() {
  let clock = Date.now();
  let requests = 0;
  let unavailable = false;
  let techName = 'Angular';
  const cards = createTechnologyCards({ apiUrl: 'https://portfolio.example/api/v1/chat/', now: () => clock,
    fetchImpl: async input => {
      const url = new URL(input);
      if (unavailable) return new Response('', { status: 503 });
      if (url.hostname === 'portfolio.example') {
        assert.equal(url.pathname, '/api/v1/tecnologias/');
        requests++;
        return Response.json({ results: [{ name: 'Frontend', technologies: [{ name: techName }] }], next: null });
      }
      assert.ok(['img.shields.io', 'github-stats-extended.vercel.app', 'github-readme-streak-stats.herokuapp.com'].includes(url.hostname));
      return new Response(svg, { headers: { 'content-type': 'image/svg+xml' } });
    },
  });
  return { cards, requests: () => requests, expire: () => { clock += 15 * 60 * 1000; },
    change: () => { techName = 'Django'; }, fail: () => { unavailable = true; } };
}

test('cards are PNG images with public technology data and refresh after 15 minutes', async () => {
  const f = sources();
  try {
    const first = await f.cards('es');
    assert.equal(first.messages.length, 2);
    assert.match(first.historyText, /Angular/);
    assert.match(first.messages[1].caption, /Consultado/);
    for (const message of first.messages) assert.equal((await sharp(message.image).metadata()).format, 'png');
    f.change();
    assert.match((await f.cards('en')).historyText, /Angular/);
    assert.equal(f.requests(), 1);
    f.expire();
    assert.match((await f.cards('es')).historyText, /Django/);
    assert.equal(f.requests(), 2);
  } finally { f.cards.close(); }
});

test('failed sources do not silently serve expired images or invented statistics', async () => {
  const f = sources();
  try {
    await f.cards('es');
    f.expire();
    f.fail();
    const result = await f.cards('es');
    assert.ok(result.messages.every(message => !message.image));
    assert.match(result.messages[0].text, /No pude cargar/);
    assert.match(result.messages[1].text, /no están disponibles/);
  } finally { f.cards.close(); }
});

test('rasterizing animated GitHub cards exposes final text without changing the data', () => {
  const animated = Buffer.from('<svg><style>.stagger{opacity: 0; animation: fadeIn 1s}</style><text style="opacity: 0;">396 contributions</text></svg>');
  const result = staticSvg(animated).toString();
  assert.ok(result.includes('396 contributions'));
  assert.ok(!result.includes('opacity: 0;'));
});

test('technology choice bypasses Groq and opt-out invalidates pending media', async () => {
  let finish;
  let questions = 0;
  const bot = new Conversation({ answer: async () => { questions++; return 'Answer'; },
    technologyCards: () => new Promise(resolve => { finish = resolve; }),
  });
  let id = 0;
  const send = text => bot.handle({ chatId: 'visitor', text, id: String(++id) });
  await send('/aubar');
  const pending = send('5');
  await send('SALIR');
  finish({ messages: [{ image: Buffer.from('png') }], historyText: 'Frontend: Angular' });
  assert.equal(await pending, null);
  assert.equal(questions, 0);
  assert.equal(await send('5'), null);
});
