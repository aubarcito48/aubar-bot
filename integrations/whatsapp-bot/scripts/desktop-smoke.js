// Test-only loopback fixture. No Baileys import, auth store, telephone or Groq.
import { createServer } from 'node:http';
import { createDesktopControl } from '../src/desktop-control.js';
const token = 'c'.repeat(64);
const phone = '12345678901';
const rows = new Map();
let sends = 0;
let notified = false;
const desktop = createDesktopControl({ token, contacts: new Set([phone]), ledger: {
  get: id => rows.get(id), start: (id, digest) => rows.set(id, { digest, status: 'pending' }),
  finish: (id, status) => { rows.get(id).status = status; },
} });
const bot = { status: () => 'connected', sendExplicit: async (recipient, text) => {
  if (recipient !== phone || text !== 'Texto de prueba local.') throw new Error('fixture_mismatch');
  sends++;
} };
const server = createServer((request, response) => {
  if (request.method === 'GET' && request.url === '/fixture/result') {
    response.writeHead(200, { 'content-type': 'application/json' }).end(JSON.stringify({ sends })); return;
  }
  void desktop.handle(request, response, bot).then(() => {
    if (!notified && request.url === '/control/events') {
      notified = true;
      desktop.notify({ chatId: phone + '@s.whatsapp.net', id: 'synthetic-only',
        text: 'Mensaje simulado para Aubar.', timestamp: Date.now() }, 'Contacto de prueba');
    }
  }).catch(() => { if (!response.headersSent) response.writeHead(503).end(); });
});
server.listen(0, '127.0.0.1', () => process.stdout.write(JSON.stringify({ port: server.address().port }) + '\n'));
process.once('SIGTERM', () => { desktop.close(); server.closeAllConnections(); server.close(); });
