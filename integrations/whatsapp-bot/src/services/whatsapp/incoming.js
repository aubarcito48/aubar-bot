/** Accept only fresh direct text messages from explicitly allowed test contacts. */
export async function readIncoming(message, contacts, resolvePhone = async () => undefined) {
  const key = message?.key;
  const jid = key?.remoteJid;
  if (key?.fromMe || !key?.id || typeof jid !== 'string' ||
      !/^\d+(?::\d+)?@(s\.whatsapp\.net|lid)$/.test(jid)) return null;
  let phoneJid = jid.endsWith('@s.whatsapp.net') ? jid : key.remoteJidAlt;
  if (!phoneJid?.endsWith('@s.whatsapp.net')) phoneJid = await resolvePhone(jid);
  if (typeof phoneJid !== 'string' || !/^\d+(?::\d+)?@s\.whatsapp\.net$/.test(phoneJid)) return null;
  const phone = phoneJid.split('@')[0].split(':')[0];
  if (!contacts.has(phone)) return null;
  const text = message.message?.conversation ?? message.message?.extendedTextMessage?.text;
  if (typeof text !== 'string') return null;
  const seconds = typeof message.messageTimestamp?.toNumber === 'function'
    ? message.messageTimestamp.toNumber() : Number(message.messageTimestamp);
  return { chatId: `${phone}@s.whatsapp.net`, replyJid: jid, id: key.id, text, timestamp: seconds * 1000 };
}
