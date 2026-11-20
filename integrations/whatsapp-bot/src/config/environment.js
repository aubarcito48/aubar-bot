import path from 'node:path';

export const DEFAULT_API = 'https://portfolio-backend-6ecn.onrender.com/api/v1/chat/';

function integer(value, fallback, min, max) {
  const parsed = value === undefined ? fallback : Number(value);
  if (!Number.isInteger(parsed) || parsed < min || parsed > max) throw new Error('Configuración numérica inválida.');
  return parsed;
}

export function readConfig(env = process.env, { requireContacts = true } = {}) {
  const api = new URL(env.PORTFOLIO_API_URL || DEFAULT_API);
  const local = ['localhost', '127.0.0.1', '[::1]'].includes(api.hostname);
  if ((api.protocol !== 'https:' && !(local && api.protocol === 'http:')) ||
      api.username || api.password || api.search || api.hash || !api.pathname.endsWith('/api/v1/chat/')) {
    throw new Error('PORTFOLIO_API_URL debe ser el endpoint /api/v1/chat/ por HTTPS (HTTP solo local).');
  }
  const contacts = (env.TEST_CONTACTS || '').split(',').map(value => value.trim()).filter(Boolean);
  if (contacts.some(value => !/^\d{8,15}$/.test(value))) throw new Error('TEST_CONTACTS admite números internacionales de 8 a 15 dígitos, sin + ni espacios.');
  if (requireContacts && !contacts.length) throw new Error('Configurá TEST_CONTACTS en .env antes de vincular WhatsApp. El bot es solo para pruebas.');
  if (env.SHOW_QR !== undefined && !['true', 'false'].includes(env.SHOW_QR)) throw new Error('SHOW_QR debe ser true o false.');
  const controlToken = env.AUBAR_CONTROL_TOKEN || '';
  if (controlToken && !/^[a-f0-9]{64}$/.test(controlToken)) throw new Error('AUBAR_CONTROL_TOKEN debe tener 64 caracteres hexadecimales.');
  return {
    apiUrl: api.href,
    timeoutMs: integer(env.API_TIMEOUT_MS, 90000, 1000, 120000),
    contacts: new Set(contacts),
    showQr: env.SHOW_QR !== 'false',
    authDir: path.resolve(env.AUTH_DIR || '.data'),
    healthHost: env.HEALTH_HOST || '127.0.0.1',
    port: integer(env.PORT, 3000, 1, 65535),
    controlToken,
  };
}
