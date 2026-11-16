"""P0-1 呈现对齐静态守卫：两棵前端树不得回退到"权威式"分析呈现。

本守卫只检查呈现层，不触碰、也不复制任何质量判定逻辑。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def test_web_render_analysis_has_no_authoritative_numbers():
    """web/ 的点评渲染不得插值精确分值、曲线或 bestMove 指令。"""
    body = _function_body(_read("web/js/app.js"), "renderAnalysis")
    for token in ("scoreLoss", "winRateCurve", "winRateChart", "analysisSummary", "bestMove"):
        assert token not in body, f"renderAnalysis 不得出现权威呈现字段: {token}"


def test_web_analysis_dialog_has_no_chart_or_gauge_dom():
    """web/ 分析弹窗不再有胜率曲线画布与五格大数字仪表。"""
    html = _read("web/index.html")
    assert 'id="winRateChart"' not in html
    assert 'id="analysisSummary"' not in html


def test_both_trees_carry_shallow_reference_label():
    """两棵前端树都要有"浅层参考"中性标注（webapp 走 i18n，web 走静态文案）。"""
    webapp_i18n = _read("webapp/js/i18n.js")
    assert "'analysis.shallow': '浅层参考'" in webapp_i18n
    assert "'analysis.shallow': 'Shallow reference'" in webapp_i18n
    assert "浅层参考" in _read("web/index.html")
    assert "analysis.shallow" in _read("webapp/index.html")


def test_webapp_progress_is_text_only():
    """webapp 的分析进度只保留"分析中 N / M 手"纯文字，不再有图形进度条。"""
    ui = _read("webapp/js/ui/app.js")
    assert ".bar i" not in ui
    assert "bar.style.width" not in ui
    assert '<div class="bar"><i></i></div>' not in _read("webapp/index.html")


def test_webapp_has_no_dead_curve_canvas():
    """webapp 受控源里死画布必须清干净：DOM、CSS、JS 引用与 i18n 键四处一起看。

    只扫受控源；`webapp/dist/` 与 `webapp/.edgeone/assets/` 是未入库的生成产物，
    由 bundle 脚本重建，不当作唯一源来守（否则守卫会盯着陈旧副本假红）。
    """
    targets = [ROOT / "webapp" / "index.html", ROOT / "webapp" / "css" / "app.css"]
    targets += sorted((ROOT / "webapp" / "js").rglob("*.js"))
    offenders: list[str] = []
    for path in targets:
        text = path.read_text(encoding="utf-8")
        for token in ("curveCanvas", "analysis.curve"):
            if token in text:
                offenders.append(f"{path.relative_to(ROOT).as_posix()}:{token}")
    assert not offenders, "webapp 受控源仍有死画布残留：" + "；".join(offenders)
