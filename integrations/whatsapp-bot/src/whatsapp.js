import makeWASocket, { DisconnectReason, makeCacheableSignalKeyStore } from '@whiskeysockets/baileys';
import pino from 'pino';
import qrcode from 'qrcode-terminal';
import { readIncoming } from './incoming.js';

export function createWhatsApp({ config, auth, conversation, onIncoming = () => {}, log = console.log, socketFactory = makeWASocket }) {
  // The library logger is silent: it can include account identifiers or keys.
  const logger = pino({ level: 'silent' });
  let socket;
  let timer;
  let stopped = false;
  let status = 'starting';
  let attempt = 0;
  let queued = 0;
  let chain = Promise.resolve();
  const terminalCodes = new Set([
    DisconnectReason.loggedOut, DisconnectReason.badSession, DisconnectReason.connectionReplaced,
    DisconnectReason.multideviceMismatch, DisconnectReason.forbidden,
  ]);

  function connect() {
    if (stopped) return;
    status = 'connecting';
    const current = socketFactory({
      auth: { creds: auth.state.creds, keys: makeCacheableSignalKeyStore(auth.state.keys, logger) },
      logger, markOnlineOnConnect: false, syncFullHistory: false, emitOwnEvents: false,
      shouldSyncHistoryMessage: () => false,
      shouldIgnoreJid: jid => !/^\d+(?::\d+)?@(s\.whatsapp\.net|lid)$/.test(jid),
      getMessage: async () => undefined,
    });
    socket = current;
    current.ev.on('creds.update', update => {
      if (stopped || socket !== current) return;
      try { auth.saveCreds(update); }
      catch { log('auth_save_failed'); stop(); }
    });
    current.ev.on('connection.update', ({ connection, lastDisconnect, qr }) => {
      if (stopped || socket !== current) return;
      if (qr) {
        status = 'waiting_for_qr';
        if (config.showQr) {
          log('Escaneá el QR desde WhatsApp > Dispositivos vinculados. No lo compartas.');
          qrcode.generate(qr, { small: true });
        } else log('qr_available_but_hidden: habilitá SHOW_QR solo en una terminal privada.');
      }
      if (connection === 'open') { attempt = 0; status = 'connected'; log('whatsapp_connected_test_mode'); }
      if (connection !== 'close') return;
      status = 'disconnected';
      const code = lastDisconnect?.error?.output?.statusCode;
      if (terminalCodes.has(code)) {
        stopped = true;
        conversation.clear();
        log('whatsapp_relink_required: sesión cerrada o reemplazada; revisá el teléfono antes de reiniciar.');
        return;
      }
      if (++attempt > 10) { stopped = true; log('whatsapp_reconnect_limit: revisá la conexión y reiniciá el proceso.'); return; }
      const delay = code === DisconnectReason.restartRequired ? 1000 : Math.min(30000, 1000 * 2 ** Math.min(attempt, 5));
      log(`whatsapp_reconnect_scheduled: ${delay}ms`);
      timer = setTimeout(connect, delay);
    });
    current.ev.on('messages.upsert', async ({ type, messages }) => {
      if (type !== 'notify' || stopped || socket !== current) return;
      for (const message of messages) {
        let incoming;
        try {
          incoming = await readIncoming(message, config.contacts,
            jid => current.signalRepository.lidMapping.getPNForLID(jid));
        } catch { log('message_filter_failed'); continue; }
        if (!incoming || stopped || socket !== current) continue;
        try { onIncoming(incoming, message.pushName); }
        catch { log('desktop_notification_failed'); }
        const execute = async () => {
          if (stopped || socket !== current) return;
          const reply = await conversation.handle(incoming);
          // Never deliver a response to another/replaced connection.
          if (reply && !stopped && socket === current && status === 'connected') {
            const messages = typeof reply === 'string' ? [{ text: reply }] : reply.messages;
            for (const content of messages) {
              if (stopped || socket !== current || status !== 'connected' || (reply.isCurrent && !reply.isCurrent())) break;
              const { fallbackText, ...payload } = content;
              try { await current.sendMessage(incoming.replyJid, payload); }
              catch (error) {
                if (!fallbackText) throw error;
                log('media_send_failed');
                if (!stopped && socket === current && status === 'connected' && (!reply.isCurrent || reply.isCurrent())) {
                  await current.sendMessage(incoming.replyJid, { text: fallbackText });
                }
              }
            }
          }
        };
        // Opt-out must invalidate an in-flight answer rather than waiting for it.
        if (['salir', 'stop', 'humano', 'human'].includes(incoming.text.trim().toLowerCase())) {
          await execute().catch(() => { log('message_processing_failed'); });
          continue;
        }
        if (queued >= 20) { log('message_queue_full'); break; }
        queued++;
        chain = chain.then(execute).catch(() => { log('message_processing_failed'); }).finally(() => { queued--; });
      }
    });
  }

  function stop() {
    stopped = true;
    clearTimeout(timer);
    status = 'stopped';
    conversation.clear();
    // end closes the transport; logout would invalidate the persisted session.
    socket?.end(undefined);
  }

  async function sendExplicit(recipient, text) {
    if (stopped || status !== 'connected' || !config.contacts.has(recipient) ||
        typeof text !== 'string' || !text.trim() || text.length > 2000) throw new Error('send_unavailable');
    const current = socket;
    const result = await current.sendMessage(`${recipient}@s.whatsapp.net`, { text });
    if (!result?.key?.id) throw new Error('send_unconfirmed');
  }
  return { start: connect, stop, status: () => status, drain: () => chain, sendExplicit };
}
