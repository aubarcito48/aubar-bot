import { whatsappText } from './whatsapp-text.js';

export class PortfolioError extends Error {
  constructor(code, retryAfter = 0) { super(code); this.code = code; this.retryAfter = retryAfter; }
}

export function validText(text, limit) {
  return typeof text === 'string' && text.trim().length > 0 && text.length <= limit &&
    !/[\p{Cc}\p{Cf}\p{Cs}]/u.test(text.replace(/[\n\r\t]/g, ''));
}

async function boundedJson(response) {
  if (!response.headers.get('content-type')?.toLowerCase().startsWith('application/json')) throw new PortfolioError('invalid_response');
  const reader = response.body?.getReader();
  if (!reader) throw new PortfolioError('invalid_response');
  const chunks = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 65536) { await reader.cancel(); throw new PortfolioError('invalid_response'); }
      chunks.push(value);
    }
    return JSON.parse(Buffer.concat(chunks).toString('utf8'));
  } finally { reader.releaseLock(); }
}

export function createPortfolioClient({ apiUrl, timeoutMs, fetchImpl = fetch }) {
  const controller = new AbortController();
  const answer = async (message, history = [], language = 'es') => {
    if (!validText(message, 1200) || !['es', 'en'].includes(language)) throw new PortfolioError('invalid_input');
    const body = JSON.stringify({ mensaje: message, historial: history, idioma: language });
    if (Buffer.byteLength(body) > 16384) throw new PortfolioError('invalid_input');
    try {
      const response = await fetchImpl(apiUrl, {
        method: 'POST', redirect: 'error', signal: AbortSignal.any([AbortSignal.timeout(timeoutMs), controller.signal]),
        headers: { 'content-type': 'application/json', accept: 'application/json' }, body,
      });
      if (!response.ok) {
        await response.body?.cancel();
        if (response.status === 429) {
          const retry = Number(response.headers.get('retry-after'));
          throw new PortfolioError('busy', Number.isFinite(retry) && retry > 0 ? Math.min(retry * 1000, 300000) : 60000);
        }
        throw new PortfolioError(response.status === 400 || response.status === 413 ? 'invalid_input' : 'unavailable');
      }
      const data = await boundedJson(response);
      if (!data || !validText(data.respuesta, 4000)) throw new PortfolioError('invalid_response');
      return whatsappText(data.respuesta);
    } catch (error) {
      if (error instanceof PortfolioError) throw error;
      throw new PortfolioError(error?.name === 'TimeoutError' || error?.name === 'AbortError' ? 'timeout' : 'unavailable');
    }
  };
  answer.close = () => controller.abort();
  return answer;
}
