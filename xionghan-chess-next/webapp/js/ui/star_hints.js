/**
 * 射·星轨：锚点放射线的数据源。
 *
 * 只做一件事：把 core 的「最近星位距离」换算成四斜方向的锚点坐标。
 * 绝不在这里重算星点集 —— 星位判定只有 core 一份（web 旧树那份是服务端
 * 序列化的 points，同样不重判）；改 core 的判定不需要改这里。
 *
 * 返回 `{row, col, stepRow, stepCol}[]`，无锚点的方向直接省略；
 * 单帧最多 4 条，调用方据此保证绘制有界。
 */

const DIAGONALS = [
  [1, 1],
  [1, -1],
  [-1, 1],
  [-1, -1],
];

export function archerAnchorRays(rules, source) {
  if (!rules || !source) return [];
  const anchors = [];
  for (const [stepRow, stepCol] of DIAGONALS) {
    const distance = rules._nearestArcherStarDistance(source, stepRow, stepCol);
    if (distance > 0) {
      anchors.push({
        row: source.row + distance * stepRow,
        col: source.col + distance * stepCol,
        stepRow,
        stepCol,
      });
    }
  }
  return anchors;
}
