import { readConfig } from '../src/config.js';
import { createPortfolioClient } from '../src/portfolio-client.js';

const config = readConfig(process.env, { requireContacts: false });
try {
  const reply = await createPortfolioClient(config)('Hola, ¿cómo te llamás y sobre qué podés ayudarme?', [], 'es');
  console.log('API del portfolio: contrato verificado. No se conectó WhatsApp.');
  console.log(reply);
} catch (error) {
  console.error(`API del portfolio: ${error.code ?? 'unavailable'}.`);
  process.exitCode = 1;
}
