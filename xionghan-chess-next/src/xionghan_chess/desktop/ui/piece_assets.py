"""棋子美术资源（三风格 PNG）的**唯一**入口。

## 为什么单开一个模块

棋子的 PNG 需要三样东西同时正确才会「看起来对」：文件名后缀（`hongche.png` 里的
`che`）、裁剪框（`PIECE_BBOX`，源图四周有留白）、以及设备像素下的缩放缓存。
任何一处散落在 `board_widget.py` / `piece_atlas.py` 里各拼一份，三处就会各自漂移：

- 后缀与网页版 `web/js/app.js` 的 `pieceAssetTypes` 是**同一套命名**。两份映射一旦
  不同步，桌面端会静默缺图（`resolve()` 返回 None → 退回字形，不报错）。
  `tests/test_desktop_pieces_assets.py` 直接解析那行 JS 与 `SUFFIX` 比对。
- 裁剪框决定盘径。源图是 160×160 但圆盘只占中间 137（传统/卡通）或 147（现代），
  四周是透明留白。**不裁直接缩放**会让棋子比字形盘小 8%~14%，切风格时肉眼可见。

## 几何：为什么裁 bbox

`0.78 × cell` 是盘径不变量（与字形模式同一份 `0.39 × cell` 半径）。裁掉留白后，
「盘径 = 图片边长」，绘制就是把一张 dev×dev 的图贴进 2R×2R 的矩形，**1:1 blit**，
不需要 `srcRect` 在绘制期缩放，也不会有「画布 ÷ 风格占比」带来的 0.5px 偏移。
`STYLE_DISK_RATIO` 因此退出绘制路径，只作为诊断常量保留（见测试里的 bbox 断言）。

## 为什么有 `_SOURCE_TREE`

仓库里棋子 PNG 只有一份真源：`web/assets/pieces/{style}/`。打包时 spec 把它映射进
`xionghan_chess/desktop/resources/pieces`，运行期就走 `theme.resource("pieces", ...)`。
但**从源码直接跑**（开发/测试）时随包资源目录里没有 `pieces/`，若只认 `theme.resource`
就永远是「三风格全缺图」——功能在开发态等于没做。所以 `resolve()` 在随包路径不存在时
回退到仓库真源；两份路径都算不出来才返回 None。回退逻辑只在本模块内，调用方仍只认
`resolve()` / `pixmap()`。

⚠️ `web/assets/pieces/**/*.png` 是 **Git LFS 跟踪**的。新克隆若没 `git lfs pull`，
拿到的是 ~130 B 的指针文本，`QPixmap` 解码失败 → 全部回退字形，**不报错**。
`packaging/build_windows.ps1` 里因此有 PNG 魔数 + 目录总字节下限的构建断言。
"""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QGuiApplication, QPixmap

from xionghan_chess.core.model import Color, PieceType

from . import theme

# 与 `web/js/app.js` 的 `pieceAssetTypes` **逐键一致**（测试会解析那一行比对）。
# `PieceType` 与美术一一对应（11 型 × 3 风格），不存在「缺图回退」。
SUFFIX: dict[PieceType, str] = {
    PieceType.KING: "han",
    PieceType.ROOK: "che",
    PieceType.HORSE: "ma",
    PieceType.ELEPHANT: "xiang",
    PieceType.ADVISOR: "shi",
    PieceType.CANNON: "pao",
    PieceType.PAWN: "bing",
    PieceType.GUARD: "wei",
    PieceType.ARCHER: "she",
    PieceType.THUNDER: "lei",
    PieceType.PATROL: "xun",
}

STYLES: tuple[str, ...] = ("traditional", "modern", "cartoon")
DEFAULT_STYLE = "traditional"

# 盘径 = 0.78 格（半径 0.39 格）。字形模式与图片模式**共用**这个不变量。
DISK_CELL_RATIO = 0.78

# 源图 160×160 里圆盘的裁剪框 `(x, y, w, h)`，66 张实测且三风格内部完全一致。
# 运行时**只读常量**，不扫 alpha、不自适应：查不到常量就按缺图处理（回退字形）。
# 换成自适应会让「美术重导出改了 padding」变成静默的尺寸漂移，而这条常量 + 测试
# 里的独立 Pillow 测量是 CI 里唯一的拦截点。
PIECE_BBOX: dict[str, tuple[int, int, int, int]] = {
    "traditional": (12, 12, 137, 137),
    "cartoon": (12, 12, 137, 137),
    "modern": (7, 7, 147, 147),
}

# 诊断常量（**不进绘制路径**）：圆盘直径 / 源图画布边长。美术实测值，
# 用来解释「为什么裁剪框是 137/147」，也便于人工复核。
STYLE_DISK_RATIO: dict[str, float] = {
    "traditional": 137 / 160,
    "modern": 147 / 160,
    "cartoon": 137 / 160,
}

# 设备像素边长的量化步进：窗口在拖拽缩放时会连续变化，若每 1px 都重新
# SmoothTransformation，一次拖拽能触发上百次重采样。4px 一档在视觉上看不出，
# 却把重采样次数压到 1/4。
EDGE_STEP = 4

# L1 原图（已裁掉留白）：`style:color:suffix` -> QPixmap（None 表示缺图/坏图）
_RAW: dict[str, QPixmap | None] = {}
# L2 预缩放：`style:color:suffix` -> (量化后的设备边长, 缩放结果)，每枚子只留最近一档
_SCALED: dict[str, tuple[int, QPixmap]] = {}
# 缺图标记：后缀缺失 / 文件不存在 / 解码失败 / 无裁剪常量。**只记一次**，避免每帧重试 IO。
_MISSING: set[str] = set()


def normalize_style(style: str | None) -> str:
    """未知风格回落到传统 —— 配置被手改成 `piece_style: "anime"` 也不该没有棋子。"""
    return style if style in PIECE_BBOX else DEFAULT_STYLE


def disk_radius(cell: float) -> float:
    """盘径半径（= 字形模式的 `0.39 × min(cw, ch)`）。"""
    return cell * DISK_CELL_RATIO / 2


def quantize_edge(dev_edge: float) -> int:
    """把设备像素边长量化到 `EDGE_STEP` 步进（至少一档）。"""
    return max(EDGE_STEP, int(round(dev_edge / EDGE_STEP)) * EDGE_STEP)


def device_edge(cell: float, device_pixel_ratio: float) -> int:
    """绘制期该请求的设备像素边长：`0.78 × cell × DPR`（量化前）。"""
    return int(round(DISK_CELL_RATIO * cell * max(1.0, device_pixel_ratio)))


def cache_key(style: str | None, color: Color, piece_type: PieceType) -> str:
    return f"{normalize_style(style)}:{color.value}:{SUFFIX.get(piece_type, '')}"


def file_name(color: Color, piece_type: PieceType) -> str | None:
    suffix = SUFFIX.get(piece_type)
    if suffix is None:
        return None
    return f"{'hong' if color is Color.RED else 'hei'}{suffix}.png"


def _source_tree() -> Path | None:
    """开发态回退：仓库里的唯一真源 `web/assets/pieces`（打包后不存在，返回 None）。"""
    for parent in Path(__file__).resolve().parents:
        candidate = parent / "web" / "assets" / "pieces"
        if candidate.is_dir():
            return candidate
    return None


def resolve(style: str | None, color: Color, piece_type: PieceType) -> Path | None:
    """棋子图片的绝对路径；该型没有美术或文件不存在时返回 None。

    **两条来源，顺序固定**：
    1. **打包态**：随包路径 `theme.resource("pieces", style, name)` —— spec 把
       `web/assets/pieces` 映射进 `resources/pieces`；
    2. 该路径不存在时（**源码态**：仓库里不复制第二份棋子图）回退到仓库真源
       `web/assets/pieces/...`（`_source_tree()` 向上定位仓库根）。
    两条路径指向**同一批文件**（`tests/test_desktop_pieces_assets.py` 断言同一枚子
    经两条路径取到的字节相同），所以开发态与打包态观感一致。
    """
    name = file_name(color, piece_type)
    if name is None:
        return None
    current = normalize_style(style)
    bundled = theme.resource("pieces", current, name)
    if bundled.is_file():
        return bundled
    source = _source_tree()
    if source is not None:
        candidate = source / current / name
        if candidate.is_file():
            return candidate
    return None


def _device_ratio() -> float:
    """当前屏幕的设备像素比；没有 GUI 应用时按 1.0 处理（不让无头调用崩）。"""
    app = QGuiApplication.instance()
    screen = app.primaryScreen() if app is not None else None
    if screen is None:
        return 1.0
    ratio = float(screen.devicePixelRatio())
    return ratio if ratio > 0 else 1.0


def _raw(style: str, color: Color, piece_type: PieceType) -> QPixmap | None:
    """L1：原图只解码 + 裁剪一次；缺图/坏图同样只判一次。"""
    key = cache_key(style, color, piece_type)
    if key in _RAW:
        return _RAW[key]
    bbox = PIECE_BBOX.get(style)
    path = resolve(style, color, piece_type)
    if bbox is None or path is None or QGuiApplication.instance() is None:
        # 没有 GUI 应用时 QPixmap 无法构造；按「缺图」记账，调用方走字形分支。
        _RAW[key] = None
        _MISSING.add(key)
        return None
    pixmap = QPixmap(str(path))
    if pixmap.isNull():
        pixmap = None
        _MISSING.add(key)
    else:
        x, y, width, height = bbox
        pixmap = pixmap.copy(QRect(x, y, width, height))
    _RAW[key] = pixmap
    return pixmap


def pixmap(style: str | None, color: Color, piece_type: PieceType,
           dev_edge: int) -> QPixmap | None:
    """取一张已裁留白、按设备像素预缩放的棋子图；缺图返回 None（调用方回退字形）。

    `dev_edge` 是**设备像素**下的盘径，量化到 `EDGE_STEP` 后作为 L2 键的一部分
    （每枚子只保留最近一档）。返回的 pixmap 已设置 devicePixelRatio，绘制时
    **不要**再 `painter.scale(dpr, dpr)` —— 那会把缩放叠乘一次，棋子放大整整一倍。
    """
    current = normalize_style(style)
    key = cache_key(current, color, piece_type)
    edge = quantize_edge(dev_edge)
    cached = _SCALED.get(key)
    if cached is not None and cached[0] == edge:
        return cached[1]
    raw = _raw(current, color, piece_type)
    if raw is None:
        return None
    scaled = raw.scaled(edge, edge, Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation)
    scaled.setDevicePixelRatio(_device_ratio())
    _SCALED[key] = (edge, scaled)
    return scaled


def is_missing(style: str | None, color: Color, piece_type: PieceType) -> bool:
    """该风格下这枚子是否已确认没有可用美术（缺型 / 缺文件 / 坏图）。"""
    return cache_key(style, color, piece_type) in _MISSING


def cached_count() -> int:
    """L1 里已解码（或已判缺）的条目数 —— 用来断言「预热真的发生过」。"""
    return len(_RAW)


def preload(style: str | None) -> int:
    """预热一个风格的全部图片（11 型 × 2 色 = 最多 22 张），返回成功解码数。

    只允许在换风格 / 构造外观时调用。`paintEvent` 里同步解码会让首帧明显卡顿，
    也会在滚动/动画时反复触发磁盘 IO。
    """
    current = normalize_style(style)
    loaded = 0
    for color in (Color.RED, Color.BLACK):
        for piece_type in SUFFIX:
            if _raw(current, color, piece_type) is not None:
                loaded += 1
    return loaded


def clear_cache() -> None:
    """清空两级缓存与缺图标记（测试用：模拟「资源后来才补上」）。"""
    _RAW.clear()
    _SCALED.clear()
    _MISSING.clear()
