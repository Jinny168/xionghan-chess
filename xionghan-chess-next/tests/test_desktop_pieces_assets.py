"""棋子美术资产守卫：张数 / 尺寸 / 命名 / 映射一致 / 裁剪框常量。

## 这个文件挡的是什么

1. **JS ↔ Python 映射漂移**：网页版 `web/js/app.js` 的 `pieceAssetTypes` 与桌面端
   `piece_assets.SUFFIX` 是同一套文件名后缀。两边一旦不同步，桌面端会**静默缺图**
   （`resolve()` 返回 None → 回退字形，不报错、不崩、只是棋子变字形）。
   这里直接解析那行 JS 与 Python 常量逐键比对。
2. **美术重导出改了留白**：`PIECE_BBOX` 是运行时裁剪用的常量。若美术重新导出时改了
   padding，棋子会静默变大或变小 —— 没有任何报错。测试用 Pillow **独立测量**
   （不调用 `piece_assets` 里任何裁剪函数），所以「测的是扫描结果 == 扫描结果」
   这种永真的假门禁不会出现。
3. **LFS 指针被当成图片**：`web/assets/pieces/**` 是 Git LFS 跟踪的。没 `git lfs pull`
   时文件是 ~130 B 的指针文本，QPixmap 解码失败 → 全部回退字形。这里验证解码失败
   会走「缺图」路径（只记一次、不抛）。
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from xionghan_chess.core.model import Color, PieceType
from xionghan_chess.desktop.ui import piece_assets, theme

ROOT = Path(__file__).resolve().parents[1]
PIECES = ROOT / "web" / "assets" / "pieces"
JS = ROOT / "web" / "js" / "app.js"
STYLES = ("traditional", "modern", "cartoon")
EXPECTED_PER_STYLE = 22


@pytest.fixture(autouse=True)
def _isolated_cache():
    """每条用例前后清空 L1/L2 与缺图标记。

    有几条用例会把 `resolve()` / `theme.resource` 打桩成「文件不存在」来验缺图路径。
    打桩会被自动还原，但 `_RAW` / `_MISSING` 是**模块级状态**，留下的「缺图」判定
    会污染后面的用例（表现为别的用例里 `pixmap()` 突然返回 None）。
    """
    piece_assets.clear_cache()
    yield
    piece_assets.clear_cache()


def _files(style: str) -> list[Path]:
    return sorted((PIECES / style).glob("*.png"))


def test_three_styles_each_have_22_png() -> None:
    for style in STYLES:
        files = _files(style)
        assert len(files) == EXPECTED_PER_STYLE, f"{style} 只有 {len(files)} 张"


def test_file_names_are_color_plus_suffix() -> None:
    suffixes = set(piece_assets.SUFFIX.values())
    for style in STYLES:
        for path in _files(style):
            match = re.fullmatch(r"(hong|hei)([a-z]+)\.png", path.name)
            assert match, f"命名不符合 hong/hei + 后缀：{path.name}"
            assert match.group(2) in suffixes, f"{path.name} 的后缀不在 SUFFIX 里"


def test_pillow_reads_every_image_as_160_square_rgba() -> None:
    pillow = pytest.importorskip("PIL.Image", reason="需要 Pillow 量图片尺寸")
    for style in STYLES:
        for path in _files(style):
            with pillow.open(path) as image:
                assert image.size == (160, 160), f"{path} 尺寸 {image.size}"
                assert image.mode == "RGBA", f"{path} 模式 {image.mode}"


def test_suffix_mapping_matches_web_js() -> None:
    """`web/js/app.js` 的 `pieceAssetTypes` 必须与 `SUFFIX` 逐键一致。"""
    source = JS.read_text(encoding="utf-8")
    match = re.search(r"const pieceAssetTypes=\{([^}]*)\}", source)
    assert match, "web/js/app.js 里找不到 pieceAssetTypes 定义"
    web = dict(re.findall(r"(\w+):'(\w+)'", match.group(1)))
    desktop = {kind.value: suffix for kind, suffix in piece_assets.SUFFIX.items()}
    assert desktop == web, f"桌面与网页的棋子命名分叉：仅桌面 {desktop.keys() - web.keys()}，" \
                           f"仅网页 {web.keys() - desktop.keys()}"


def test_all_11_art_types_resolve_in_all_styles() -> None:
    paths: set[Path] = set()
    for style in STYLES:
        for color in (Color.RED, Color.BLACK):
            for kind in piece_assets.SUFFIX:
                path = piece_assets.resolve(style, color, kind)
                assert path is not None, f"{style}/{color.value}/{kind.value} 解析不到图片"
                assert path.is_file()
                paths.add(path)
    assert len(paths) == len(STYLES) * 2 * len(piece_assets.SUFFIX) == 66




def test_unknown_style_falls_back_to_traditional() -> None:
    path = piece_assets.resolve("anime", Color.RED, PieceType.KING)
    assert path is not None and path.parent.name == "traditional"


# ---------------------------------------------------------------------------
# 裁剪框常量：用 Pillow **独立**测量，不调用 piece_assets 的裁剪代码
# ---------------------------------------------------------------------------
def _measured_bbox(path: Path) -> tuple[int, int, int, int]:
    pillow = pytest.importorskip("PIL.Image", reason="需要 Pillow 量 alpha")
    with pillow.open(path) as image:
        alpha = image.convert("RGBA").getchannel("A")
        # 阈值取 128 而不是 >0：将来美术加抗锯齿边时，>0 会把羽化外沿也算进盘径。
        mask = alpha.point(lambda value: 255 if value >= 128 else 0)
        left, top, right, bottom = mask.getbbox()
    return left, top, right - left, bottom - top


@pytest.mark.parametrize("style", STYLES)
def test_bbox_constants_match_measured_alpha_bounds(style: str) -> None:
    """三风格各 22 张，实测 `(x, y, w, h)` 必须与 `PIECE_BBOX` 完全相同（不放容差）。"""
    expected = piece_assets.PIECE_BBOX[style]
    for path in _files(style):
        assert _measured_bbox(path) == expected, f"{path.name} 的裁剪框变了：{_measured_bbox(path)}"


def test_bbox_is_square_and_centered() -> None:
    """盘径必须是正方形且居中 —— 否则绘制中心会与字形模式错位。"""
    for style, (left, top, width, height) in piece_assets.PIECE_BBOX.items():
        assert width == height, f"{style} 裁剪框不是正方形：{width}×{height}"
        assert width in (137, 147), f"{style} 裁剪框边长异常：{width}"
        center_x = left + width / 2
        center_y = top + height / 2
        assert abs(center_x - 80.5) <= 0.75, f"{style} 水平不居中：{center_x}"
        assert abs(center_y - 80.5) <= 0.75, f"{style} 垂直不居中：{center_y}"


def test_disk_ratio_table_matches_bbox() -> None:
    """`STYLE_DISK_RATIO` 只是诊断常量，但必须与裁剪框自洽（别写成别的数）。"""
    for style, (_x, _y, width, _h) in piece_assets.PIECE_BBOX.items():
        assert piece_assets.STYLE_DISK_RATIO[style] == pytest.approx(width / 160, abs=1e-4)


# ---------------------------------------------------------------------------
# 缓存与量化
# ---------------------------------------------------------------------------
def test_quantize_edge_snaps_to_four_pixel_steps() -> None:
    assert piece_assets.quantize_edge(55) == 56
    assert piece_assets.quantize_edge(56) == 56
    assert piece_assets.quantize_edge(58) == 56
    assert piece_assets.quantize_edge(0) == piece_assets.EDGE_STEP


def test_device_edge_is_disk_diameter_in_device_pixels() -> None:
    """`dev = 0.78 × cell × DPR` —— 与字形盘径同一个矩形。"""
    assert piece_assets.device_edge(100, 1.0) == 78
    assert piece_assets.device_edge(100, 2.0) == 156
    assert piece_assets.device_edge(60.97, 1.0) == 48




def test_broken_image_is_treated_as_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """LFS 指针 / 损坏文件：解码失败要落到「缺图」，不抛异常。"""
    piece_assets.clear_cache()
    pointer = tmp_path / "honghan.png"
    pointer.write_text("version https://git-lfs.github.com/spec/v1\noid sha256:abc\nsize 123\n",
                       encoding="utf-8")
    monkeypatch.setattr(piece_assets, "resolve", lambda *args, **kwargs: pointer)
    assert piece_assets.pixmap("traditional", Color.RED, PieceType.KING, 60) is None
    assert piece_assets.is_missing("traditional", Color.RED, PieceType.KING)


def test_bundled_and_source_paths_resolve_to_the_same_bytes(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """源码态与打包态取到的是**同一批文件**。

    仓库里棋子图只有一份真源（`web/assets/pieces`），打包时由 spec 映射进随包目录。
    开发态随包目录不存在，`resolve()` 会回退到真源 —— 这条断言两边的字节一致，
    否则「开发时看到的」和「用户看到的」会是两套图。
    """
    bundled = piece_assets.resolve("traditional", Color.RED, PieceType.KING)
    assert bundled is not None and "web" in bundled.parts
    monkeypatch.setattr(theme, "resource", lambda *parts: tmp_path.joinpath(*parts))
    source = piece_assets.resolve("traditional", Color.RED, PieceType.KING)
    assert source is not None, "随包路径缺失时应回退到仓库真源"
    assert source.read_bytes() == bundled.read_bytes()


def test_bundled_path_wins_when_it_exists(
        tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """打包态优先：随包路径存在时**不得**再去读仓库真源。"""
    bundled_dir = tmp_path / "pieces" / "traditional"
    bundled_dir.mkdir(parents=True)
    real = piece_assets.resolve("modern", Color.RED, PieceType.ROOK)
    assert real is not None
    target = bundled_dir / "hongche.png"
    target.write_bytes(real.read_bytes())
    monkeypatch.setattr(theme, "resource",
                        lambda *parts: tmp_path.joinpath(*parts))
    resolved = piece_assets.resolve("traditional", Color.RED, PieceType.ROOK)
    assert resolved == target


def test_missing_art_still_falls_back_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """回退路径**不依赖具体兵种**：把解析器打成"永远找不到图"，验证三条语义。

    甲/楯/刺硬删除后，真实世界已没有"缺图型"；但回退分支必须留着（将来新增兵种
    美术没跟上时兜底），所以这里用 monkeypatch 造一个"没有美术"的输入，
    而不是拿某个具体类型当样本。
    """
    piece_assets.clear_cache()
    calls: list[PieceType] = []
    real = piece_assets.resolve

    def missing(style, color, kind):
        calls.append(kind)
        return None

    monkeypatch.setattr(piece_assets, "resolve", missing)
    for _ in range(5):
        assert piece_assets.pixmap("traditional", Color.RED, PieceType.PAWN, 60) is None
    assert calls == [PieceType.PAWN], f"缺图被重复探测了 {len(calls)} 次（缓存失效）"
    assert piece_assets.is_missing("traditional", Color.RED, PieceType.PAWN)
    monkeypatch.setattr(piece_assets, "resolve", real)


def test_missing_art_still_falls_back_and_caches(monkeypatch: pytest.MonkeyPatch) -> None:
    """回退路径**不依赖具体兵种**：把解析器打成"永远找不到图"，验证三条语义。

    甲/楯/刺硬删除后，真实世界已没有"缺图型"；但回退分支必须留着（将来新增兵种
    美术没跟上时兜底），所以这里用 monkeypatch 造一个"没有美术"的输入，
    而不是拿某个具体类型当样本。
    """
    piece_assets.clear_cache()
    calls: list[PieceType] = []
    real = piece_assets.resolve

    def missing(style, color, kind):
        calls.append(kind)
        return None

    monkeypatch.setattr(piece_assets, "resolve", missing)
    for _ in range(5):
        assert piece_assets.pixmap("traditional", Color.RED, PieceType.PAWN, 60) is None
    assert calls == [PieceType.PAWN], f"缺图被重复探测了 {len(calls)} 次（缓存失效）"
    assert piece_assets.is_missing("traditional", Color.RED, PieceType.PAWN)
    monkeypatch.setattr(piece_assets, "resolve", real)
