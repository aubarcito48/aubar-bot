import sharp from 'sharp';
import styles from './readme-cards.json' with { type: 'json' };
import { sectionQuestion } from '../conversation/menu.js';

const TTL = 15 * 60 * 1000;
const escape = value => String(value).replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&apos;' })[char]);
const normalized = value => value.toLowerCase().replace(/[^a-z0-9+]/g, '');
const stamp = now => new Intl.DateTimeFormat('es-AR', { timeZone: 'America/Argentina/Buenos_Aires', dateStyle: 'short', timeStyle: 'short' }).format(new Date(now)) + ' (Argentina)';

export function staticSvg(buffer) {
  // SVG viewers play CSS animations; a PNG renderer captures their invisible first frame.
  const svg = buffer.toString('utf8').replace(/opacity:\s*0(?:\.0+)?\s*;/g, 'opacity: 1;');
  const offset = svg.match(/@keyframes rankAnimation[\s\S]*?to\s*\{\s*stroke-dashoffset:\s*([\d.]+)/)?.[1];
  return Buffer.from(svg.replace('</svg>', `<style>.stagger{opacity:1!important;animation:none!important}.rank-circle{animation:none!important;${offset ? `stroke-dashoffset:${offset};` : ''}}.rank-text{animation:none!important}</style></svg>`));
}

async function mapLimited(items, worker) {
  const result = new Array(items.length);
  let cursor = 0;
  await Promise.all(Array.from({ length: Math.min(6, items.length) }, async () => {
    while (cursor < items.length) {
      const index = cursor++;
      result[index] = await worker(items[index]);
    }
  }));
  return result;
}

export function isTechnologyChoice(text, language) {
  return sectionQuestion(text, language) === sectionQuestion('5', language);
}

async function download(url, { fetchImpl, timeoutMs = 15000, signal, json = false }) {
  const response = await fetchImpl(url, { redirect: 'error',
    signal: AbortSignal.any([AbortSignal.timeout(timeoutMs), signal]),
    headers: { accept: json ? 'application/json' : 'image/svg+xml' } });
  if (!response.ok) { await response.body?.cancel(); throw new Error('card_source_unavailable'); }
  if (!response.headers.get('content-type')?.includes(json ? 'application/json' : 'image/svg+xml')) {
    await response.body?.cancel(); throw new Error('card_source_invalid');
  }
  const chunks = [];
  let size = 0;
  for await (const chunk of response.body) {
    size += chunk.length;
    if (size > 1024 * 1024) throw new Error('card_source_oversized');
    chunks.push(chunk);
  }
  const buffer = Buffer.concat(chunks);
  if (json) return JSON.parse(buffer.toString('utf8'));
  const svg = buffer.toString('utf8');
  if (!svg.includes('<svg') || /Something went wrong|Could not fetch|rate limit exceeded|Service Unavailable|Invalid username/i.test(svg)) {
    throw new Error('card_source_invalid');
  }
  return buffer;
}

function fallbackBadge(name) {
  const width = Math.min(820, Math.max(90, name.length * 17 + 32));
  return Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="36"><rect width="100%" height="100%" rx="6" fill="#253548"/><text x="16" y="25" fill="#e6edf3" font-family="Arial" font-size="22">${escape(name)}</text></svg>`);
}

export function createTechnologyCards({ apiUrl, timeoutMs = 90000, fetchImpl = fetch, now = Date.now }) {
  const controller = new AbortController();
  const options = { fetchImpl, signal: controller.signal };
  let cache;
  let pending;

  async function groups() {
    const base = new URL('../tecnologias/', apiUrl);
    let next = base.href;
    const grouped = new Map();
    const visited = new Set();
    while (next) {
      const url = new URL(next, base);
      if (url.origin !== base.origin || url.pathname !== base.pathname || url.username || url.password || visited.has(url.href) || visited.size >= 5) {
        throw new Error('card_pagination_invalid');
      }
      visited.add(url.href);
      const data = await download(url.href, { ...options, json: true, timeoutMs });
      if (!Array.isArray(data.results)) throw new Error('card_data_invalid');
      for (const group of data.results) {
        if (typeof group.name !== 'string' || group.name.length > 100 || !Array.isArray(group.technologies)) throw new Error('card_data_invalid');
        const entries = grouped.get(group.name) ?? new Set();
        for (const item of group.technologies) {
          if (typeof item.name !== 'string' || !item.name.trim() || item.name.length > 100) throw new Error('card_data_invalid');
          entries.add(item.name.trim());
        }
        grouped.set(group.name, entries);
      }
      next = data.next;
    }
    if (!grouped.size || grouped.size > 12 || [...grouped.values()].reduce((sum, names) => sum + names.size, 0) > 100) throw new Error('card_data_invalid');
    return [...grouped].map(([name, entries]) => ({ name, technologies: [...entries].filter(item =>
      !(item === 'HTML' && entries.has('HTML5')) && !(item === 'CSS' && entries.has('CSS3'))) }));
  }

  async function technologyImage(data, time) {
    const overlays = [];
    const text = [];
    let y = 150;
    for (const group of data) {
      text.push(`<text x="40" y="${y}" fill="#58a6ff" font-size="27" font-weight="bold">${escape(group.name)}</text>`);
      y += 22;
      let x = 40;
      const badges = await mapLimited(group.technologies, async name => {
        const alias = { html: 'html5', css: 'css3', restapis: 'restapi' }[normalized(name)] ?? normalized(name);
        const source = Object.entries(styles.badges).find(([label]) => normalized(label) === alias)?.[1];
        let svg;
        try { svg = source ? await download(source, options) : fallbackBadge(name); }
        catch { svg = fallbackBadge(name); }
        return sharp(svg, { limitInputPixels: 4e6 }).resize({ height: 38, width: 820, fit: 'inside' }).png().toBuffer({ resolveWithObject: true });
      });
      for (const badge of badges) {
        if (x + badge.info.width > 920) { x = 40; y += 56; }
        overlays.push({ input: badge.data, left: x, top: y });
        x += badge.info.width + 14;
      }
      y += 100;
    }
    const height = y + 90;
    const background = Buffer.from(`<svg xmlns="http://www.w3.org/2000/svg" width="960" height="${height}"><rect width="100%" height="100%" rx="24" fill="#0d1117"/><g font-family="Arial"><text x="40" y="58" font-size="34" font-weight="bold" fill="#e6edf3">Nahuel Argandoña</text><text x="40" y="100" font-size="23" fill="#8b949e">Tecnologías · Portfolio</text>${text.join('')}<text x="40" y="${height - 48}" font-size="19" fill="#8b949e">Consultado: ${time}</text><text x="40" y="${height - 20}" font-size="17" fill="#8b949e">Fuente: portfolio publicado · Logos: estilo del README</text></g></svg>`);
    return sharp(background).composite(overlays).png().toBuffer();
  }

  async function build() {
    const fetchedAt = now();
    const statsPromise = Promise.allSettled(styles.stats.map(async source => {
      const svg = await download(source.url, options);
      return sharp(staticSvg(svg), { limitInputPixels: 4e6 }).resize({ width: 880 }).flatten({ background: '#0d1117' }).png().toBuffer({ resolveWithObject: true });
    }));
    let data;
    let tech;
    try { data = await groups(); tech = await technologyImage(data, stamp(fetchedAt)); } catch { /* Reply reports this source unavailable. */ }
    const stats = await statsPromise;
    const valid = stats.filter(item => item.status === 'fulfilled').map(item => item.value);
    let statistics;
    if (valid.length) {
      let y = 20;
      const layers = valid.map(item => { const layer = { input: item.data, left: 20, top: y }; y += item.info.height + 20; return layer; });
      statistics = await sharp({ create: { width: 920, height: y, channels: 3, background: '#0d1117' } }).composite(layers).png().toBuffer();
    }
    return { fetchedAt, tech, statistics, groups: data, missingStats: stats.length - valid.length };
  }

  async function load(language) {
    if (!cache || now() - cache.fetchedAt >= TTL) {
      pending ??= build().finally(() => { pending = undefined; });
      const result = await pending;
      // Retry on the next request if either source failed; never reuse stale snapshots.
      cache = result.tech && result.statistics && !result.missingStats ? result : undefined;
      return reply(result, language);
    }
    return reply(cache, language);
  }

  function reply(data, language) {
    const es = language === 'es';
    const techText = data.groups?.map(group => `${group.name}: ${group.technologies.join(', ')}`).join('\n\n');
    const messages = [];
    if (data.tech) messages.push({ image: data.tech, caption: es ? 'Tecnologías de Nahuel · Fuente: portfolio publicado.' : "Nahuel’s technologies · Source: published portfolio.", fallbackText: techText });
    else messages.push({ text: es ? 'No pude cargar la tarjeta de tecnologías. Podés consultar el portfolio o intentarlo de nuevo.' : 'The technology card could not be loaded. Check the portfolio or try again.' });
    if (data.statistics) messages.push({ image: data.statistics, caption: `${es ? 'Actividad de GitHub' : 'GitHub activity'} · @${styles.username}\n${es ? 'Consultado' : 'Fetched'}: ${stamp(data.fetchedAt)}\n${es ? 'Los proveedores pueden mostrar datos en caché. El uso de lenguajes no mide dominio profesional.' : 'Providers may cache their data. Language usage is not a measure of proficiency.'}`, fallbackText: es ? 'No pude enviar la imagen de estadísticas. Podés ver la actividad en https://github.com/aubarcito48' : 'The statistics image could not be sent. See activity at https://github.com/aubarcito48' });
    if (!data.statistics || data.missingStats) messages.push({ text: es ? 'Algunas estadísticas no están disponibles ahora. Podés ver la actividad en https://github.com/aubarcito48' : 'Some statistics are unavailable right now. See activity at https://github.com/aubarcito48' });
    return { messages, historyText: [techText, data.statistics ? `${es ? 'Se mostraron estadísticas de GitHub' : 'GitHub statistics were shown'} (${stamp(data.fetchedAt)}).` : 'GitHub statistics unavailable.'].filter(Boolean).join('\n\n') };
  }

  load.close = () => controller.abort();
  return load;
}
