import { mkdirSync, writeFileSync } from 'node:fs';
import { readConfig } from '../src/config.js';
import { createTechnologyCards } from '../src/technology-cards.js';

const cards = createTechnologyCards(readConfig(process.env, { requireContacts: false }));
try {
  const result = await cards('es');
  mkdirSync('tmp/cards-preview', { recursive: true });
  let index = 0;
  for (const message of result.messages) {
    if (message.image) {
      const filename = `tmp/cards-preview/card-${++index}.png`;
      writeFileSync(filename, message.image);
      console.log(filename);
    }
    console.log(message.caption ?? message.text);
  }
} finally { cards.close(); }
