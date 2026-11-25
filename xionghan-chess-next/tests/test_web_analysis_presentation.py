"""P0-1 呈现对齐守卫：前端两棵树与桌面复盘都不得回退到"权威式"分析呈现。

本守卫只检查呈现层，不触碰、也不复制任何质量判定逻辑。桌面端原先只在
`tests/test_review_report.py` 里守"无指导句式"，不守"无精确分值"—— 于是
`report.py` 的"评分下降 {loss}"、百分比胜率曲线与 `dialogs.py` 的"损失 {loss}"
一路留到了 P0-1 收口。这里把同一口径扩到桌面。
"""

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# 桌面复盘的呈现面：report.py 产出报告正文，dialogs.py 把它和逐手档位拼成弹窗。
DESKTOP_REPORT = "src/xionghan_chess/desktop/ui/report.py"
DESKTOP_DIALOGS = "src/xionghan_chess/desktop/ui/dialogs.py"


def _read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8")


def _function_body(source: str, name: str) -> str:
    marker = f"function {name}("
    start = source.index(marker)
    end = source.find("\nfunction ", start + len(marker))
    return source[start:] if end == -1 else source[start:end]


def _python_function_body(source: str, name: str) -> str:
    """取 Python 方法体：`def name(` 所在行起，到缩进不深于 def 的行为止。"""
    lines = source.splitlines()
    for index, line in enumerate(lines):
        if f"def {name}(" in line:
            indent = len(line) - len(line.lstrip())
            body = [line]
            for follow in lines[index + 1 :]:
                if follow.strip() and len(follow) - len(follow.lstrip()) <= indent:
                    break
                body.append(follow)
            return "\n".join(body)
    raise AssertionError(f"源码里找不到函数 {name}")


_DESKTOP_RESULT = {
    "analyzedPlies": 6,
    "summary": {"best": 2, "good": 1, "inaccuracy": 1, "mistake": 1, "blunder": 1},
    "winRateCurve": [50.0, 40.0, 30.0, 28.0, 32.0, 35.0],
    "moves": [
        {"ply": 1, "notation": "漢六進一", "quality": "best", "scoreLoss": 0},
        {"ply": 2, "notation": "車八平七", "quality": "good", "scoreLoss": 15},
        {"ply": 3, "notation": "炮二平五", "quality": "inaccuracy", "scoreLoss": 120},
        {"ply": 4, "notation": "馬三進四", "quality": "mistake", "scoreLoss": 300},
        {"ply": 5, "notation": "卒五進一", "quality": "blunder", "scoreLoss": 500},
        {"ply": 6, "notation": "相三進五", "quality": "best", "scoreLoss": 0},
    ],
}


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


# ── 桌面复盘：同一口径（轻量非权威，不显示精确分值）───────────────────────────


def test_desktop_report_renders_no_scores_or_percentages():
    """桌面报告正文不得出现失分数值或百分比：档位文字才是呈现面。

    只断言渲染结果，不禁止 `report.py` 内部保留 `score_loss` 字段 ——
    `core/analysis.py` 的 score/scoreLoss/winRate 仍是数据，只是不上屏。
    """
    from xionghan_chess.desktop.ui.report import build_report

    blob = "\n".join(build_report(_DESKTOP_RESULT).lines)
    assert "%" not in blob, f"桌面报告仍以百分比呈现胜率：{blob}"
    for loss in ("500", "300", "120"):
        assert loss not in blob, f"桌面报告仍显示失分数值 {loss}：{blob}"
    assert "评分下降" not in blob, f"桌面报告仍在讲分值升降：{blob}"
    assert "浅层参考" in blob, f"桌面报告缺少\"浅层参考\"中性标注：{blob}"


def test_desktop_report_source_has_no_score_copy():
    """报告源码里的文案常量不得回退到分值 / 百分比口径。"""
    source = _read(DESKTOP_REPORT)
    assert "评分下降" not in source, "report.py 仍有\"评分下降\"文案"
    assert "胜率曲线由" not in source, "report.py 仍以百分比描述胜率曲线"
    assert "浅层参考" in source, "report.py 缺少\"浅层参考\"中性标注"


def test_desktop_analysis_dialog_has_no_loss_number():
    """`_show_analysis_result` 的逐手清单只留档位，不带损失数值。"""
    body = _python_function_body(_read(DESKTOP_DIALOGS), "_show_analysis_result")
    for token in ("损失", "scoreLoss", "{loss}"):
        assert token not in body, f"桌面逐手清单仍呈现失分：{token}"
    assert "浅层参考" in body, "桌面逐手清单缺少\"浅层参考\"中性标注"
