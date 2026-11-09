const test = require('node:test');
const assert = require('node:assert');
const { createSession, applySnapshot } = require('./state.js');

test('new room resets baseline and accepts first frame', () => {
  const session = createSession('OLD');
  session.revision = 42;
  const result = applySnapshot(session, { roomId: 'NEW', revision: 0 });
  assert.equal(result.accept, true);
  assert.equal(result.reason, 'new-room');
  assert.equal(session.roomId, 'NEW');
  assert.equal(session.revision, 0);
});

test('stale frame in the same room is dropped', () => {
  const session = createSession('R');
  session.revision = 7;
  const result = applySnapshot(session, { roomId: 'R', revision: 6 });
  assert.equal(result.accept, false);
  assert.equal(result.reason, 'stale');
  assert.equal(session.revision, 7);
});

test('duplicate frame is accepted but does not mark a revision change', () => {
  const session = createSession('R');
  session.revision = 3;
  const result = applySnapshot(session, { roomId: 'R', revision: 3 });
  assert.equal(result.accept, true);
  assert.equal(result.reason, 'duplicate');
  assert.equal(result.revisionChanged, false);
});

test('forward frame is accepted and marks a revision change', () => {
  const session = createSession('R');
  session.revision = 3;
  const result = applySnapshot(session, { roomId: 'R', revision: 4 });
  assert.equal(result.accept, true);
  assert.equal(result.reason, 'new-revision');
  assert.equal(result.revisionChanged, true);
  assert.equal(session.revision, 4);
});

test('invalid snapshot is rejected', () => {
  const session = createSession('R');
  const result = applySnapshot(session, { roomId: 'R' });
  assert.equal(result.accept, false);
  assert.equal(result.reason, 'invalid');
});
