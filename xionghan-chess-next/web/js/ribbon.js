// 横幅状态的**唯一判定口**：将军时给 `.turn-ribbon` 挂 `is-check`（CSS 里换成 #7f1d1d/#fff）。
// 单独成模块是为了能在 node 里直接 import 验证，不必起浏览器。
export function ribbonClass(state) {
  return state && state.check ? 'turn-ribbon is-check' : 'turn-ribbon';
}

// 脉冲中点色：在 #7f1d1d 再压深一档，绝不回到品牌绿。
export const CHECK_PULSE_MID = '#4a1010';
