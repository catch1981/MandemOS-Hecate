const test = require('node:test');
const assert = require('node:assert');
const child_process = require('child_process');
const { verifyToken } = require('./hecate-auto');

test('verifyToken logs GitHub username on success', (t) => {
  t.mock.method(child_process, 'execSync', () =>
    Buffer.from('{"login":"testuser"}')
  );
  const messages = [];
  t.mock.method(console, 'log', (msg) => messages.push(msg));
  verifyToken('dummy');
  assert.strictEqual(
    messages[0],
    'Authenticated with GitHub API as testuser'
  );
});
