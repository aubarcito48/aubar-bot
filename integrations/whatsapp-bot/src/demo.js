import { createInterface } from 'node:readline/promises';
import { readConfig } from './config.js';
import { createPortfolioClient } from './portfolio-client.js';
import { Conversation } from './conversation.js';

const mock = process.argv.includes('--mock');
const config = readConfig(process.env, { requireContacts: false });
const answer = mock
  ? async message => `Respuesta simulada a «${message}». Este modo no consulta Render ni conecta WhatsApp.`
  : createPortfolioClient(config);
const bot = new Conversation({ answer });
const rl = createInterface({ input: process.stdin, output: process.stdout });
console.log(mock ? 'Demo sin red ni WhatsApp.' : 'Demo con la API real del portfolio; las preguntas se envían a Render/Groq.');
console.log('Escribí /aubar o /aubar en para empezar; SALIR apaga el bot, /fin cierra esta demo.');
let id = 0;
try {
  for await (const text of rl) {
    if (text.trim() === '/fin') break;
    const reply = await bot.handle({ chatId: 'local-demo', id: String(++id), text });
    console.log(reply ?? '(Sin respuesta automática.)');
  }
} finally { bot.clear(); answer.close?.(); rl.close(); }
