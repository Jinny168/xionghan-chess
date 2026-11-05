// 网页横幅将军态的最小验证（无需浏览器）：node scripts/verify_ribbon.mjs
// 期望输出：将军: turn-ribbon is-check | 非将军: turn-ribbon | 脉冲中点: #4a1010
import { ribbonClass, CHECK_PULSE_MID } from '../web/js/ribbon.js';
console.log('将军:', ribbonClass({ check: true }),
            '| 非将军:', ribbonClass({ check: false }),
            '| 脉冲中点:', CHECK_PULSE_MID);
