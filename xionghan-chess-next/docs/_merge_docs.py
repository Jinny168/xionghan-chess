import re
from pathlib import Path

DOCS = Path(__file__).resolve().parent


def load(title_line, path):
    text = (DOCS / path).read_text(encoding="utf-8")
    # Replace the first top-level "# " heading with "## " so the merged doc
    # keeps a single top-level title with nested sections.
    lines = text.splitlines()
    for i, ln in enumerate(lines):
        if ln.startswith("# ") and not ln.startswith("## "):
            # Keep the original wording but demote to level 2.
            lines[i] = "## " + ln[2:].lstrip()
            break
    return title_line + "\n\n" + "\n".join(lines).strip() + "\n"


def build(filename, top_title, sections):
    parts = [f"# {top_title}\n"]
    parts.append("\n> 本文件由 v1.3.0 迭代中的多份输出文档归并而成，"
                 "保留完整审计痕迹，便于单点查阅。\n")
    # index
    parts.append("## 目录\n")
    for idx, (sec_title, _) in enumerate(sections, 1):
        parts.append(f"{idx}. {sec_title}")
    parts.append("")
    parts.append("---\n")
    for sec_title, path in sections:
        parts.append(load(f"## {sec_title}", path))
        parts.append("\n---\n")
    out = "\n".join(parts).rstrip() + "\n"
    (DOCS / filename).write_text(out, encoding="utf-8")
    print(f"wrote {filename}: {len(out.splitlines())} lines")


# QA lifecycle: report -> remediation -> audit -> audit-remediation -> delivery
build(
    "QA_v1.3.0.md",
    "匈汉象棋 v1.3.0 质量保障与交付总览",
    [
        ("一、三端一致性校验与隐藏Bug报告（QA_REPORT）", "QA_REPORT_v1.3.0.md"),
        ("二、缺陷整改记录（QA_REMEDIATION）", "QA_REMEDIATION_v1.3.0.md"),
        ("三、缺陷修复二次复核审计（QA_AUDIT）", "QA_AUDIT_v1.3.0.md"),
        ("四、二次审计整改记录（QA_AUDIT_REMEDIATION）", "QA_AUDIT_REMEDIATION_v1.3.0.md"),
        ("五、1.3.0 迭代交付说明（DELIVERY）", "DELIVERY_1.3.0.md"),
    ],
)

# AI work: plan -> implementation
build(
    "AI_v1.3.0.md",
    "匈汉象棋 AI 引擎优化 v1.3.0（方案 + 实施 + 审计）",
    [
        ("一、AI 引擎优化方案（AI_OPTIMIZATION）", "AI_OPTIMIZATION_v1.3.0.md"),
        ("二、AI 优化实施记录（AI_OPTIMIZATION_IMPLEMENTATION）",
         "AI_OPTIMIZATION_IMPLEMENTATION_v1.3.0.md"),
    ],
)
