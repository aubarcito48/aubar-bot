import { createServer } from 'node:http';
import { readConfig } from './config/environment.js';
import { createPortfolioClient } from './services/portfolio/client.js';
import { Conversation } from './services/conversation/conversation.js';
import { openAuthStore } from './storage/auth-store.js';
import { createWhatsApp } from './services/whatsapp/whatsapp.js';
import { createTechnologyCards } from './services/portfolio/technology-cards.js';
import { createDesktopControl, openSendLedger } from './services/desktop/control.js';

let auth;
let bot;
let server;
let answer;
let technologyCards;
let desktop;
let ledger;
let closing = false;

async function shutdown() {
  if (closing) return;
  closing = true;
  desktop?.close();
  bot?.stop();
  answer?.close();
  technologyCards?.close();
  server?.close();
  // Abort in-flight HTTP, discard its reply, then release the session store.
  if (bot) await bot.drain();
  await desktop?.drain();
  auth?.close();
  ledger?.close();
}

try {
  const config = readConfig();
  auth = openAuthStore(config.authDir);
  answer = createPortfolioClient(config);
  technologyCards = createTechnologyCards(config);
  const conversation = new Conversation({ answer, technologyCards, onError: code => console.log(`portfolio_${code}`) });
  if (config.controlToken) ledger = openSendLedger(config.authDir);
  desktop = createDesktopControl({ token: config.controlToken, contacts: config.contacts, ledger });
  bot = createWhatsApp({ config, auth, conversation, onIncoming: desktop.notify });
  server = createServer((request, response) => {
    if (request.url?.startsWith('/control/')) {
      void desktop.handle(request, response, bot).catch(() => {
        if (!response.headersSent && !response.destroyed) response.writeHead(503, { 'content-type': 'application/json' }).end('{"error":"unavailable"}');
      });
      return;
    }
    const status = bot.status();
    const health = request.method === 'GET' && request.url === '/health';
    response.writeHead(health ? (status === 'connected' ? 200 : 503) : 404, {
      'content-type': 'application/json', 'cache-control': 'no-store', 'x-content-type-options': 'nosniff',
    });
    response.end(JSON.stringify(health ? { status } : { error: 'not_found' }));
  });
  server.requestTimeout = 10000;
  server.headersTimeout = 10000;
  server.on('error', () => { console.error('health_server_failed'); void shutdown().then(() => { process.exitCode = 1; }); });
  server.listen(config.port, config.healthHost, () => {
    console.log('Aubar WhatsApp: modo de prueba. Solo responderá a TEST_CONTACTS tras /aubar o el mensaje del portfolio.');
    try { bot.start(); }
    catch { console.error('whatsapp_start_failed'); void shutdown().then(() => { process.exitCode = 1; }); }
  });
  for (const signal of ['SIGINT', 'SIGTERM']) process.once(signal, () => { void shutdown(); });
} catch (error) {
  // Config errors are authored here; no provider errors/credentials are printed.
  if (!auth) console.error('No se pudo iniciar. Configurá TEST_CONTACTS y PORTFOLIO_API_URL en .env; revisá AUTH_DIR y usá un solo proceso por sesión.');
  else console.error('No se pudo iniciar el microservicio.');
  await shutdown();
  process.exitCode = 1;
}
