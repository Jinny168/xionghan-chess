/* Minimal client state contract shared by the web UI.
 *
 * 三段状态里的「服务端权威」一层：只负责房间/revision 的接受规则，
 * 不碰 preferences、不碰 DOM。桌面端有同名 Python 实现
 * (desktop/snapshot_guard.py)，两端规则必须逐条一致。
 */
(function (root) {
  'use strict';

  function createSession(roomId) {
    return { roomId: roomId || null, revision: -1 };
  }

  function applySnapshot(session, snapshot) {
    if (!session) session = createSession();
    if (!snapshot || typeof snapshot.revision !== 'number') {
      return { accept: false, reason: 'invalid', revisionChanged: false };
    }
    var incomingRoom = snapshot.roomId || null;
    var newRoom = session.roomId !== incomingRoom;
    if (newRoom) {
      // 新房间的 revision 从 0/1 重新开始；先把基线打到 -1，
      // 否则首帧会被「只许前进」的守卫当成过期帧丢掉。
      session.roomId = incomingRoom;
      session.revision = -1;
    }
    if (!newRoom && snapshot.revision < session.revision) {
      return { accept: false, reason: 'stale', revisionChanged: false };
    }
    var changed = snapshot.revision !== session.revision;
    session.revision = snapshot.revision;
    return {
      accept: true,
      reason: newRoom ? 'new-room' : (changed ? 'new-revision' : 'duplicate'),
      revisionChanged: changed,
    };
  }

  var api = { createSession: createSession, applySnapshot: applySnapshot };
  root.XHState = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(typeof globalThis !== 'undefined' ? globalThis : this);
