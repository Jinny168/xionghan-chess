/**
 * 棋盘渲染器。
 *
 * 全部用 Canvas 绘制，不依赖任何图片资源：棋盘、长城阴山分界、九宫、
 * 星轨、初始位角标、棋子、动画都在这里完成。
 */

import { RED_NAMES, BLACK_NAMES } from '../core/profiles.js';

const THEMES = {
  classic: {
    paper: ['#f3e3c3', '#e6cfa4'],
    edge: '#b98c53',
    line: '#7a5327',
    lineSoft: 'rgba(122,83,39,.42)',
    text: '#8a5a2b',
    mark: 'rgba(122,83,39,.55)',
    shadow: 'rgba(60,35,10,.28)',
    frame: '#8a5a2b',
  },
  jade: {
    paper: ['#e8efdf', '#d3e0c4'],
    edge: '#93a987',
    line: '#4e6647',
    lineSoft: 'rgba(78,102,71,.4)',
    text: '#5c7351',
    mark: 'rgba(78,102,71,.45)',
    shadow: 'rgba(30,50,25,.24)',
    frame: '#5c7351',
  },
  ink: {
    paper: ['#3a3a3c', '#26262a'],
    edge: '#5c5c62',
    line: '#b9b3a6',
    lineSoft: 'rgba(185,179,166,.36)',
    text: '#cfc7b4',
    mark: 'rgba(207,199,180,.4)',
    shadow: 'rgba(0,0,0,.5)',
    frame: '#6d6a63',
  },
};

const GLYPH_FONT = '"KaiTi","STKaiti","Kaiti SC","Noto Serif SC","Songti SC",serif';
const UI_FONT = '"PingFang SC","Microsoft YaHei",system-ui,sans-serif';

export class BoardRenderer {
  constructor(canvas) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.size = 0;
    this.dpr = 1;
    this.geometry = null;
  }

  /** 按宽度定尺寸，高度由行列比推出（传统象棋 9×10 不会被压扁）。 */
  resize(cssWidth, rows, cols) {
    const pad = cssWidth * 0.062;
    const cell = (cssWidth - pad * 2) / (cols - 1);
    const cssHeight = pad * 2 + (rows - 1) * cell;
    const dpr = Math.min(window.devicePixelRatio || 1, 2.5);
    this.canvas.width = Math.max(1, Math.round(cssWidth * dpr));
    this.canvas.height = Math.max(1, Math.round(cssHeight * dpr));
    this.canvas.style.width = `${cssWidth}px`;
    this.canvas.style.height = `${cssHeight}px`;
    this.width = cssWidth;
    this.height = cssHeight;
    this.dpr = dpr;
  }

  computeGeometry(view) {
    const rows = view.profile.rows;
    const cols = view.profile.cols;
    const w = this.width;
    const pad = w * 0.062;
    const cell = (w - pad * 2) / (cols - 1);
    const h = pad * 2 + (rows - 1) * cell;
    this.geometry = { rows, cols, w, h, pad, cell };
    return this.geometry;
  }

  /** 屏幕坐标 → 棋盘交叉点。 */
  hitTest(clientX, clientY, view) {
    if (!this.geometry) return null;
    const rect = this.canvas.getBoundingClientRect();
    const { rows, cols, pad, cell } = this.geometry;
    let col = Math.round((clientX - rect.left - pad) / cell);
    let row = Math.round((clientY - rect.top - pad) / cell);
    const dx = clientX - rect.left - (pad + col * cell);
    const dy = clientY - rect.top - (pad + row * cell);
    if (Math.hypot(dx, dy) > cell * 0.62) return null;
    if (view.flipped) {
      row = rows - 1 - row;
      col = cols - 1 - col;
    }
    if (row < 0 || row >= rows || col < 0 || col >= cols) return null;
    return { row, col };
  }

  screenPos(row, col, view) {
    const { rows, cols, pad, cell } = this.geometry;
    const r = view.flipped ? rows - 1 - row : row;
    const c = view.flipped ? cols - 1 - col : col;
    return { x: pad + c * cell, y: pad + r * cell };
  }

  draw(view) {
    if (!this.width || !this.height) return; // 首帧布局尚未完成
    const ctx = this.ctx;
    const geom = this.computeGeometry(view);
    const { w, h, pad, cell, rows, cols } = geom;
    const theme = THEMES[view.theme] || THEMES.classic;
    const dpr = this.dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.clearRect(0, 0, w, h);

    this.drawBoardSurface(view, theme, geom);

    ctx.save();
    ctx.lineCap = 'round';
    ctx.strokeStyle = theme.line;
    ctx.lineWidth = Math.max(1, w * 0.0016);

    if (rows === 13) this.drawXionghanGrid(view, theme, geom);
    else this.drawClassicGrid(view, theme, geom);

    this.drawPalaces(theme, geom);
    if (rows === 13) {
      if (view.showMarks !== false) this.drawInitialMarks(theme, geom, view);
      this.drawStarLattice(theme, geom, view);
    }
    ctx.restore();

    this.drawLastMove(view, theme, geom);
    this.drawSelection(view, theme, geom);
    this.drawTargets(view, theme, geom);
    this.drawPieces(view, theme, geom, view.anim ? view.anim.piece.id : null);
    if (view.anim) this.drawAnimation(view, theme, geom);
    this.drawCoordinates(view, theme, geom);
    void pad;
  }

  drawBoardSurface(view, theme, geom) {
    const ctx = this.ctx;
    const { w, h } = geom;
    const size = Math.min(w, h);
    const radius = size * 0.018;
    const gradient = ctx.createLinearGradient(0, 0, w, h);
    gradient.addColorStop(0, theme.paper[0]);
    gradient.addColorStop(1, theme.paper[1]);
    ctx.save();
    ctx.beginPath();
    roundRect(ctx, 0, 0, w, h, radius);
    ctx.fillStyle = gradient;
    ctx.fill();

    // 纸纹：稀疏的斜向纹理，成本很低但能去掉纯色塑料感
    ctx.clip();
    ctx.globalAlpha = view.theme === 'ink' ? 0.05 : 0.045;
    ctx.strokeStyle = theme.line;
    ctx.lineWidth = 1;
    const step = Math.max(5, size / 42);
    for (let x = -h; x < w + h; x += step) {
      ctx.beginPath();
      ctx.moveTo(x, 0);
      ctx.lineTo(x + h, h);
      ctx.stroke();
    }
    ctx.globalAlpha = 1;

    // 四角暗角
    const vignette = ctx.createRadialGradient(w / 2, h / 2, size * 0.2, w / 2, h / 2, size * 0.78);
    vignette.addColorStop(0, 'rgba(0,0,0,0)');
    vignette.addColorStop(1, view.theme === 'ink' ? 'rgba(0,0,0,.32)' : 'rgba(90,55,20,.14)');
    ctx.fillStyle = vignette;
    ctx.fillRect(0, 0, w, h);
    ctx.restore();
  }

  drawXionghanGrid(view, theme, geom) {
    const ctx = this.ctx;
    const { pad, cell, rows, cols } = geom;
    void rows;
    ctx.strokeStyle = theme.line;
    for (let r = 0; r < 13; r += 1) {
      if (r === 6) continue;
      line(ctx, pad, pad + r * cell, pad + (cols - 1) * cell, pad + r * cell);
    }
    for (let c = 0; c < 13; c += 1) {
      line(ctx, pad + c * cell, pad, pad + c * cell, pad + 5 * cell);
      line(ctx, pad + c * cell, pad + 7 * cell, pad + c * cell, pad + 12 * cell);
    }
    // 外框加粗
    ctx.save();
    ctx.strokeStyle = theme.frame;
    ctx.lineWidth = Math.max(2, geom.w * 0.0042);
    line(ctx, pad, pad, pad + 12 * cell, pad);
    line(ctx, pad, pad + 12 * cell, pad + 12 * cell, pad + 12 * cell);
    line(ctx, pad, pad, pad, pad + 12 * cell);
    line(ctx, pad + 12 * cell, pad, pad + 12 * cell, pad + 12 * cell);
    ctx.restore();

    this.drawBoundaryBand(view, theme, geom);
  }

  drawBoundaryBand(view, theme, geom) {
    const ctx = this.ctx;
    const { pad, cell, w } = geom;
    const size = w;
    const y = pad + 6 * cell;
    const left = pad;
    const right = pad + 12 * cell;
    const tick = Math.min(cell, size * 0.06) * 0.42;

    ctx.save();
    ctx.strokeStyle = theme.lineSoft;
    ctx.lineWidth = Math.max(1, size * 0.0015);
    for (let c = 0; c < 13; c += 1) {
      const x = pad + c * cell;
      line(ctx, x - tick, y, x + tick, y);
      if (c > 0 && c < 12) line(ctx, x, y - tick, x, y + tick);
    }

    // 长城 / 阴山：字号随棋盘缩放，用底色描边保证不被刻线干扰
    const fontSize = Math.max(11, cell * 0.44);
    ctx.font = `600 ${fontSize}px ${GLYPH_FONT}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = fontSize * 0.34;
    ctx.strokeStyle = theme.paper[0];
    ctx.fillStyle = theme.text;
    const labels = [
      { text: '长 城', col: 3.2 },
      { text: '阴 山', col: 8.8 },
    ];
    for (const label of labels) {
      const x = pad + label.col * cell;
      ctx.strokeText(label.text, x, y);
      ctx.fillText(label.text, x, y);
    }
    ctx.restore();
    void left;
    void right;
    void view;
  }

  drawClassicGrid(view, theme, geom) {
    const ctx = this.ctx;
    const { pad, cell, cols } = geom;
    ctx.strokeStyle = theme.line;
    for (let r = 0; r < 10; r += 1) line(ctx, pad, pad + r * cell, pad + 8 * cell, pad + r * cell);
    for (let c = 0; c < 9; c += 1) {
      if (c === 0 || c === 8) {
        line(ctx, pad + c * cell, pad, pad + c * cell, pad + 9 * cell);
      } else {
        line(ctx, pad + c * cell, pad, pad + c * cell, pad + 4 * cell);
        line(ctx, pad + c * cell, pad + 5 * cell, pad + c * cell, pad + 9 * cell);
      }
    }
    const y = pad + 4.5 * cell;
    const fontSize = Math.max(12, cell * 0.5);
    ctx.save();
    ctx.font = `500 ${fontSize}px ${GLYPH_FONT}`;
    ctx.fillStyle = theme.text;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('楚 河', pad + 2 * cell, y);
    ctx.fillText('漢 界', pad + 6 * cell, y);
    ctx.restore();
    void cols;
    void view;
  }

  drawPalaces(theme, geom) {
    const ctx = this.ctx;
    const { pad, cell, rows } = geom;
    const palaces = rows === 10 ? [[0, 3], [7, 3]] : [[1, 5], [9, 5]];
    ctx.save();
    ctx.strokeStyle = theme.lineSoft;
    ctx.lineWidth = Math.max(1, geom.w * 0.0016);
    for (const [r, c] of palaces) {
      line(ctx, pad + c * cell, pad + r * cell, pad + (c + 2) * cell, pad + (r + 2) * cell);
      line(ctx, pad + (c + 2) * cell, pad + r * cell, pad + c * cell, pad + (r + 2) * cell);
    }
    ctx.restore();
  }

  drawStarLattice(theme, geom, view) {
    const points = view.profile.archerStarPoints || [];
    if (!points.length) return;
    const ctx = this.ctx;
    const { pad, cell, w } = geom;
    const size = w;
    const inner = Math.min(cell, size * 0.05) * 0.6;
    const outer = inner * 2.6;
    ctx.save();
    ctx.strokeStyle = theme.mark;
    ctx.lineWidth = Math.max(1, size * 0.0014);
    for (const point of points) {
      const x = pad + point.col * cell;
      const y = pad + point.row * cell;
      for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
        line(ctx, x + sx * inner, y + sy * inner, x + sx * outer, y + sy * outer);
      }
    }
    ctx.restore();
  }

  drawInitialMarks(theme, geom, view) {
    const ctx = this.ctx;
    const { pad, cell, w } = geom;
    const size = w;
    const positions = [];
    for (const r of [4, 8]) for (let c = 0; c < 13; c += 2) positions.push([r, c]);
    positions.push([3, 1], [3, 11], [9, 1], [9, 11]);
    const offset = Math.min(cell, size * 0.06) * 0.34;
    const length = offset * 1.5;
    ctx.save();
    ctx.strokeStyle = theme.mark;
    ctx.lineWidth = Math.max(1, size * 0.0014);
    for (const [r, c] of positions) {
      const x = pad + c * cell;
      const y = pad + r * cell;
      for (const [sx, sy] of [[-1, -1], [1, -1], [-1, 1], [1, 1]]) {
        const cx = x + sx * offset;
        const cy = y + sy * offset;
        line(ctx, cx, cy, cx + sx * length, cy);
        line(ctx, cx, cy, cx, cy + sy * length);
      }
    }
    ctx.restore();
    void view;
  }

  drawLastMove(view, theme, geom) {
    const last = view.lastMove;
    if (!last) return;
    const ctx = this.ctx;
    const { cell } = geom;
    ctx.save();
    for (const [point, alpha] of [[last.source, 0.3], [last.target, 0.42]]) {
      const { x, y } = this.screenPos(point.row, point.col, view);
      ctx.fillStyle = `rgba(196,146,44,${alpha})`;
      ctx.beginPath();
      ctx.arc(x, y, cell * 0.46, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
    void theme;
  }

  drawSelection(view, theme, geom) {
    if (!view.selected) return;
    const ctx = this.ctx;
    const { cell } = geom;
    const { x, y } = this.screenPos(view.selected.row, view.selected.col, view);
    ctx.save();
    ctx.strokeStyle = '#c9a227';
    ctx.lineWidth = Math.max(2, cell * 0.055);
    ctx.shadowColor = 'rgba(201,162,39,.55)';
    ctx.shadowBlur = cell * 0.22;
    ctx.beginPath();
    ctx.arc(x, y, cell * 0.46, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
    void theme;
  }

  drawTargets(view, theme, geom) {
    const ctx = this.ctx;
    const { cell } = geom;
    const occupied = new Set(view.state.pieces.map((p) => `${p.row},${p.col}`));
    ctx.save();
    for (const target of view.legal || []) {
      const { x, y } = this.screenPos(target.row, target.col, view);
      if (occupied.has(`${target.row},${target.col}`)) {
        ctx.strokeStyle = 'rgba(176,58,46,.85)';
        ctx.lineWidth = Math.max(2, cell * 0.045);
        ctx.beginPath();
        ctx.arc(x, y, cell * 0.45, 0, Math.PI * 2);
        ctx.stroke();
      } else {
        ctx.fillStyle = 'rgba(58,104,72,.78)';
        ctx.beginPath();
        ctx.arc(x, y, cell * 0.145, 0, Math.PI * 2);
        ctx.fill();
        ctx.strokeStyle = 'rgba(255,250,238,.75)';
        ctx.lineWidth = Math.max(1, cell * 0.028);
        ctx.stroke();
      }
    }
    ctx.restore();
    void theme;
  }

  drawPieces(view, theme, geom, skipId) {
    const ctx = this.ctx;
    for (const piece of view.state.pieces) {
      if (skipId && piece.id === skipId) continue;
      const { x, y } = this.screenPos(piece.row, piece.col, view);
      this.drawPiece(ctx, piece, x, y, geom, theme, view);
    }
  }

  drawPiece(ctx, piece, x, y, geom, theme, view) {
    const { cell } = geom;
    const r = cell * 0.42;
    const style = view.pieceStyle || 'traditional';
    const isRed = piece.color === 'red';
    const ink = isRed ? '#a3271f' : '#2b2622';
    const inkDark = isRed ? '#7d1a14' : '#171412';

    ctx.save();
    ctx.shadowColor = theme.shadow;
    ctx.shadowBlur = r * 0.42;
    ctx.shadowOffsetY = r * 0.14;

    const gradient = ctx.createRadialGradient(x - r * 0.35, y - r * 0.4, r * 0.2, x, y, r * 1.05);
    if (view.theme === 'ink') {
      gradient.addColorStop(0, isRed ? '#5c2a26' : '#3a3733');
      gradient.addColorStop(1, isRed ? '#331715' : '#1d1b19');
    } else {
      gradient.addColorStop(0, '#fff8e8');
      gradient.addColorStop(0.62, '#f2ddb4');
      gradient.addColorStop(1, '#ddbe8a');
    }
    ctx.beginPath();
    ctx.arc(x, y, r, 0, Math.PI * 2);
    ctx.fillStyle = gradient;
    ctx.fill();
    ctx.shadowColor = 'transparent';

    ctx.lineWidth = Math.max(1.4, r * (style === 'modern' ? 0.1 : 0.085));
    ctx.strokeStyle = view.theme === 'ink' ? (isRed ? '#e0685e' : '#c8c0b2') : ink;
    ctx.stroke();

    if (style === 'traditional') {
      ctx.beginPath();
      ctx.arc(x, y, r * 0.83, 0, Math.PI * 2);
      ctx.lineWidth = Math.max(1, r * 0.045);
      ctx.strokeStyle = view.theme === 'ink' ? (isRed ? 'rgba(224,104,94,.5)' : 'rgba(200,192,178,.4)') : `${ink}66`;
      ctx.stroke();
    }

    if (style === 'ink') {
      const wash = ctx.createRadialGradient(x, y, r * 0.1, x, y, r);
      wash.addColorStop(0, 'rgba(0,0,0,0)');
      wash.addColorStop(1, isRed ? 'rgba(90,20,16,.4)' : 'rgba(0,0,0,.32)');
      ctx.beginPath();
      ctx.arc(x, y, r * 0.98, 0, Math.PI * 2);
      ctx.fillStyle = wash;
      ctx.fill();
    }

    const names = isRed ? RED_NAMES : BLACK_NAMES;
    const glyph = names[piece.type] || piece.type;
    const fontSize = style === 'modern' ? r * 1.02 : r * 1.14;
    ctx.font = style === 'modern'
      ? `600 ${fontSize}px ${UI_FONT}`
      : `600 ${fontSize}px ${GLYPH_FONT}`;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillStyle = view.theme === 'ink'
      ? (isRed ? '#f0a79f' : '#ddd5c5')
      : inkDark;
    ctx.fillText(glyph, x, y + r * 0.04);
    ctx.restore();

    if (view.checkSide === piece.color && piece.type === 'king') {
      const pulse = 0.5 + 0.5 * Math.sin(performance.now() / 260);
      ctx.save();
      ctx.strokeStyle = `rgba(200,40,30,${0.5 + pulse * 0.45})`;
      ctx.lineWidth = Math.max(2, cell * 0.05);
      ctx.beginPath();
      ctx.arc(x, y, r * (1.1 + pulse * 0.06), 0, Math.PI * 2);
      ctx.stroke();
      ctx.restore();
    }
  }

  drawAnimation(view, theme, geom) {
    const anim = view.anim;
    const t = Math.min(1, (performance.now() - anim.started) / anim.duration);
    const eased = 1 - (1 - t) ** 3;
    const from = this.screenPos(anim.from.row, anim.from.col, view);
    const to = this.screenPos(anim.to.row, anim.to.col, view);
    const x = from.x + (to.x - from.x) * eased;
    const y = from.y + (to.y - from.y) * eased;
    const ctx = this.ctx;
    ctx.save();
    ctx.globalAlpha = 1;
    this.drawPiece(ctx, anim.piece, x, y, geom, theme, view);
    if (anim.capture) {
      const { x: cx, y: cy } = to;
      ctx.globalAlpha = (1 - t) * 0.7;
      ctx.strokeStyle = 'rgba(176,58,46,.9)';
      ctx.lineWidth = Math.max(2, geom.cell * 0.05);
      ctx.beginPath();
      ctx.arc(cx, cy, geom.cell * (0.3 + t * 0.35), 0, Math.PI * 2);
      ctx.stroke();
    }
    ctx.restore();
  }

  drawCoordinates(view, theme, geom) {
    if (!view.showCoordinates) return;
    const ctx = this.ctx;
    const { pad, cell, rows, cols, w, h } = geom;
    const size = w;
    ctx.save();
    ctx.font = `500 ${Math.max(8, size * 0.0125)}px ${UI_FONT}`;
    ctx.fillStyle = theme.text;
    ctx.globalAlpha = 0.5;
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    for (let c = 0; c < cols; c += 1) {
      const x = pad + c * cell;
      ctx.fillText(String.fromCharCode(65 + c), x, pad * 0.5);
      ctx.fillText(String.fromCharCode(65 + c), x, h - pad * 0.42);
    }
    ctx.textAlign = 'left';
    for (let r = 0; r < rows; r += 1) {
      const y = pad + r * cell;
      ctx.fillText(String(r + 1), pad * 0.42, y);
    }
    ctx.restore();
  }
}

function line(ctx, x1, y1, x2, y2) {
  ctx.beginPath();
  ctx.moveTo(x1, y1);
  ctx.lineTo(x2, y2);
  ctx.stroke();
}

function roundRect(ctx, x, y, w, h, r) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}

export { THEMES };
