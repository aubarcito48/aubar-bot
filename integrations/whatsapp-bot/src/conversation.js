import { PortfolioError, validText } from './portfolio-client.js';
import { isMenuRequest, menuText, sectionQuestion } from './menu.js';
import { isTechnologyChoice } from './technology-cards.js';

export const TRIGGERS = new Map([
  ['Hola Nahuel, vi tu portfolio y me gustaría contactarte.', 'es'],
  ['Hi Nahuel, I saw your portfolio and would like to get in touch.', 'en'],
  ['/aubar', 'es'], ['/aubar en', 'en'],
]);
const STOP = new Set(['salir', 'stop', 'humano', 'human']);
const WELCOME = {
  es: `¡Hola! Soy Aubar, el asistente de IA del portfolio de Nahuel 👋\n\n${menuText('es')}\n\nTus consultas se procesan con Groq. Escribí SALIR o HUMANO para desactivar las respuestas automáticas; no garantiza una respuesta personal de Nahuel.`,
  en: `Hi! I'm Aubar, the AI assistant for Nahuel's portfolio 👋\n\n${menuText('en')}\n\nQuestions are processed with Groq. Send STOP or HUMAN to disable automated replies; this does not guarantee a personal response from Nahuel.`,
};
const TTL = 30 * 60 * 1000;

export class Conversation {
  constructor({ answer, technologyCards, now = Date.now, onError = () => {} }) {
    this.answer = answer;
    this.technologyCards = technologyCards;
    this.now = now;
    this.onError = onError;
    this.sessions = new Map();
    this.seen = new Map();
    this.globalRequests = [];
    this.cooldownUntil = 0;
    this.generation = 0;
  }

  clear() { this.generation++; this.sessions.clear(); this.seen.clear(); }

  async handle({ chatId, id, text, timestamp = this.now() }) {
    const now = this.now();
    for (const [key, expiry] of this.seen) if (expiry <= now) this.seen.delete(key);
    for (const [key, session] of this.sessions) if (session.expires <= now) this.sessions.delete(key);
    if (!chatId || !id || !validText(text, 1200) || !Number.isFinite(timestamp) || Math.abs(now - timestamp) > 300000) return null;
    const key = `${chatId}:${id}`;
    if (this.seen.has(key)) return null;
    this.seen.set(key, now + 300000);
    if (this.seen.size > 10000) this.seen.delete(this.seen.keys().next().value);
    text = text.trim();
    let session = this.sessions.get(chatId);
    const firstActivation = !session;
    const language = TRIGGERS.get(text);
    if (!session && !language) return null;
    if (session && STOP.has(text.toLowerCase())) {
      this.sessions.delete(chatId);
      return session.language === 'es' ? 'Bot desactivado. No recibirás más respuestas automáticas.' : 'Bot disabled. Automated replies are now off.';
    }
    if (!session) {
      if (this.sessions.size >= 100) return null;
      session = { language, history: [], requests: [], expires: now + TTL };
      this.sessions.set(chatId, session);
    }
    session.requests = session.requests.filter(time => time > now - 60000);
    if (session.requests.length >= 5) return null;
    session.requests.push(now);
    session.expires = now + TTL;
    if (language) {
      session.language = language;
      // The model must see the greeting already delivered in WhatsApp.
      // Reactivation changes language but preserves the conversation's context.
      const reply = firstActivation ? WELCOME[language] : language === 'es'
        ? 'Seguimos por acá. Podés hacerme otra pregunta o escribir MENÚ para ver las secciones.'
        : 'We can keep going here. Ask another question or send MENU to see the sections.';
      session.history.push({ role: 'user', content: text }, { role: 'assistant', content: reply });
      this.trimHistory(session);
      return reply;
    }
    if (isMenuRequest(text)) {
      const reply = menuText(session.language);
      session.history.push({ role: 'user', content: text }, { role: 'assistant', content: reply });
      this.trimHistory(session);
      return reply;
    }
    if (this.technologyCards && isTechnologyChoice(text, session.language)) {
      const generation = this.generation;
      const isCurrent = () => generation === this.generation && this.sessions.get(chatId) === session;
      try {
        const reply = await this.technologyCards(session.language);
        if (!isCurrent()) return null;
        session.history.push({ role: 'user', content: sectionQuestion('5', session.language) },
          { role: 'assistant', content: reply.historyText.slice(0, 2000) });
        this.trimHistory(session);
        return { ...reply, isCurrent };
      } catch {
        this.onError('cards_unavailable');
        if (!isCurrent()) return null;
        return session.language === 'es' ? 'No pude cargar las tarjetas. Probá de nuevo en un momento.' : 'The cards could not be loaded. Please try again shortly.';
      }
    }
    // Send the actual section intent, not an ambiguous digit, to the API and history.
    text = sectionQuestion(text, session.language) ?? text;
    this.globalRequests = this.globalRequests.filter(time => time > now - 60000);
    if (now < this.cooldownUntil || this.globalRequests.length >= 8) {
      return session.language === 'es' ? 'Aubar está ocupado. Probá de nuevo en un minuto.' : 'Aubar is busy. Try again in a minute.';
    }
    this.globalRequests.push(now);
    const generation = this.generation;
    try {
      const reply = await this.answer(text, [...session.history], session.language);
      if (generation !== this.generation || this.sessions.get(chatId) !== session) return null;
      session.history.push({ role: 'user', content: text }, { role: 'assistant', content: reply.slice(0, 2000) });
      this.trimHistory(session);
      return reply;
    } catch (error) {
      if (generation !== this.generation || this.sessions.get(chatId) !== session) return null;
      const code = error instanceof PortfolioError ? error.code : 'unexpected';
      if (code === 'busy') this.cooldownUntil = now + (error.retryAfter || 60000);
      this.onError(code); // Only a bounded code, never content, numbers or error bodies.
      return session.language === 'es'
        ? 'Ahora no puedo consultar el portfolio. Intentá otra vez en un momento.'
        : "I can't reach the portfolio right now. Please try again shortly.";
    }
  }

  trimHistory(session) {
    while (session.history.length > 8 || session.history.reduce((sum, item) => sum + item.content.length, 0) > 6000) session.history.splice(0, 2);
  }
}
