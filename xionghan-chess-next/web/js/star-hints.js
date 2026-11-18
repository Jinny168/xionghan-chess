/**
 * 射·星轨锚点（web 旧树）。
 *
 * 旧树没有 `_nearestArcherStarDistance`：星点集来自 /api/profiles 下发的
 * `archerStarPoints`（core 序列化的权威数据），走法判定在服务端。
 * 这里只做纯几何 —— 从 source 沿四斜方向逐格走，命中 points 里的第一个格即锚点；
 * 出盘即停。绝不在 JS 重新判断"哪些点是星位"（那会在前端长出第二份规则）。
 *
 * 返回 `[{row, col, stepRow, stepCol}]`，单帧至多 4 条。
 */
(function () {
  'use strict';
  const DIAGONALS = [[1, 1], [1, -1], [-1, 1], [-1, -1]];

  function archerAnchorRays(points, source, rows, cols) {
    if (!Array.isArray(points) || !points.length || !source) return [];
    const starSet = new Set(points.map((point) => `${point.row},${point.col}`));
    const anchors = [];
    const limit = Math.max(rows, cols);
    for (const [stepRow, stepCol] of DIAGONALS) {
      for (let distance = 1; distance < limit; distance += 1) {
        const row = source.row + distance * stepRow;
        const col = source.col + distance * stepCol;
        if (row < 0 || row >= rows || col < 0 || col >= cols) break;
        if (starSet.has(`${row},${col}`)) {
          anchors.push({ row, col, stepRow, stepCol });
          break;
        }
      }
    }
    return anchors;
  }

  globalThis.XHStarHints = { archerAnchorRays };
})();
