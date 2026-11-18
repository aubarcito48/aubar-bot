import { mkdirSync, chmodSync } from 'node:fs';
import path from 'node:path';
import { DatabaseSync } from 'node:sqlite';
import { BufferJSON, initAuthCreds, proto } from '@whiskeysockets/baileys';

/** Auth only. Conversations never enter this file. Run one bot process per DB. */
export function openAuthStore(directory) {
  mkdirSync(directory, { recursive: true, mode: 0o700 });
  const filename = path.join(directory, 'auth.sqlite');
  const db = new DatabaseSync(filename);
  try {
    chmodSync(filename, 0o600);
    db.exec(`PRAGMA busy_timeout=1000; PRAGMA locking_mode=EXCLUSIVE;
      CREATE TABLE IF NOT EXISTS auth (kind TEXT NOT NULL, id TEXT NOT NULL, value TEXT NOT NULL,
      PRIMARY KEY (kind, id)); BEGIN EXCLUSIVE; COMMIT;`);
    const select = db.prepare('SELECT value FROM auth WHERE kind = ? AND id = ?');
    const upsert = db.prepare('INSERT INTO auth(kind, id, value) VALUES (?, ?, ?) ON CONFLICT(kind,id) DO UPDATE SET value=excluded.value');
    const remove = db.prepare('DELETE FROM auth WHERE kind = ? AND id = ?');
    const read = (kind, id) => {
      const row = select.get(kind, id);
      return row ? JSON.parse(row.value, BufferJSON.reviver) : undefined;
    };
    const creds = read('credentials', 'main') ?? initAuthCreds();
    return {
      state: {
        creds,
        keys: {
          get: async (kind, ids) => Object.fromEntries(ids.map(id => {
            let value = read(kind, id);
            if (kind === 'app-state-sync-key' && value) value = proto.Message.AppStateSyncKeyData.fromObject(value);
            return [id, value];
          })),
          set: async data => {
            db.exec('BEGIN IMMEDIATE');
            try {
              for (const [kind, keys] of Object.entries(data)) {
                for (const [id, value] of Object.entries(keys)) {
                  if (value == null) remove.run(kind, id);
                  else upsert.run(kind, id, JSON.stringify(value, BufferJSON.replacer));
                }
              }
              db.exec('COMMIT');
            } catch (error) { db.exec('ROLLBACK'); throw error; }
          },
        },
      },
      saveCreds: update => {
        Object.assign(creds, update);
        upsert.run('credentials', 'main', JSON.stringify(creds, BufferJSON.replacer));
      },
      close: () => db.close(),
    };
  } catch (error) { db.close(); throw error; }
}
