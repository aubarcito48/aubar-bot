import { test } from 'node:test';
import assert from 'node:assert/strict';
import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { openAuthStore } from '../src/auth-store.js';

test('SQLite preserves binary session keys and credentials across a normal restart', async () => {
  const directory = mkdtempSync(path.join(tmpdir(), 'aubar-auth-'));
  let store;
  try {
    store = openAuthStore(directory);
    store.saveCreds({ registered: true });
    const publicKey = store.state.creds.signedIdentityKey.public;
    await store.state.keys.set({ session: { 'test-key': Buffer.from([1, 2, 3]) } });
    store.close();
    store = openAuthStore(directory);
    assert.equal(store.state.creds.registered, true);
    assert.deepEqual(store.state.creds.signedIdentityKey.public, publicKey);
    assert.deepEqual((await store.state.keys.get('session', ['test-key']))['test-key'], Buffer.from([1, 2, 3]));
    await store.state.keys.set({ session: { 'test-key': null } });
    assert.equal((await store.state.keys.get('session', ['test-key']))['test-key'], undefined);
  } finally {
    store?.close();
    const relative = path.relative(path.resolve(tmpdir()), path.resolve(directory));
    if (!relative || relative.startsWith('..') || path.isAbsolute(relative) || !path.basename(directory).startsWith('aubar-auth-')) {
      throw new Error('Temporary test directory escaped the expected root.');
    }
    rmSync(directory, { recursive: true, force: true });
  }
});
