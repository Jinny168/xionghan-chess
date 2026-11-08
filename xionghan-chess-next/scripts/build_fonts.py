"""生成随包开源字体（阶段2 S2-4）：Noto Sans SC / Noto Serif SC 的 GB2312 子集。

## 为什么要换字体
原随包字体是 Windows 自带的 `msyh.ttc`（微软雅黑）与 `simkai.ttf`（楷体），
合计 31.5 MB。这两个是**微软授权字体**，随安装包分发需要单独授权 ——
项目此前是直接把系统字体拷进仓库，授权状态未查证（计划文档第 178 行记为「未查证」）。

替换为 Noto Sans SC / Noto Serif SC：由 Adobe 与 Google 联合开发（即「思源黑体 /
思源宋体」的 Google 版本），**SIL Open Font License 1.1**。已核实条款：
- 允许 merge / embed / modify / redistribute，允许随软件分发；
- 条件 2：每份拷贝须包含版权声明与本许可（本脚本产出旁边的 LICENSE）；
- 条件 3：修改版**不得使用保留字体名** —— 子集化属于 Modified Version，
  因此这里把 family 名改掉（见 `SUBSET_FAMILY`），不沿用 "Noto Sans SC"。

## 为什么是「GB2312 全级」而不是「只收项目用到的字」
第一版按项目源码里出现过的 802 个汉字取子集，两文件仅 1.19 MB —— 很有诱惑力，
但那样**用户昵称 / 聊天内容 / 棋谱标题里任何未收录的字都会变成方块**。
折中取 GB2312 全部 6763 汉字 + 项目自有字符（含 27 个棋子字形，其中
檑/礌/䠶/碷/䠶 等不在 GB2312 内，靠项目字符补齐），共约 7558 字，
覆盖日常中文阅读，两个文件合计约 9.8 MB（比原来省 21.7 MB）。

## 用法
    python scripts/build_fonts.py --source-dir C:/Windows/Fonts
    # 产物写入 src/xionghan_chess/desktop/resources/fonts/
    # 需要 fonttools（pip install fonttools），只在**换字体时**跑一次

## 许可合规
脚本会把 OFL 许可全文写到 `resources/fonts/OFL.txt`，与字体一起随包分发。
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
FONT_DIR = PROJECT_ROOT / "src" / "xionghan_chess" / "desktop" / "resources" / "fonts"

# 子集后的 family 名。OFL 条件 3：Modified Version 不得使用保留字体名，
# 故加 "Subset" 后缀明确区分（这也是「改名」而不是「冒充原版」）。
SUBSET_FAMILY = {
    "NotoSansSC-VF.ttf": ("Noto Sans SC Subset", "Noto Sans SC Subset"),
    "NotoSerifSC-VF.ttf": ("Noto Serif SC Subset", "Noto Serif SC Subset"),
}

# 输出文件名 —— 与 theme.load_bundled_fonts() 里注册的一致。
OUTPUT_NAME = {
    "NotoSansSC-VF.ttf": "NotoSansSC-subset.ttf",
    "NotoSerifSC-VF.ttf": "NotoSerifSC-subset.ttf",
}

OFL_TEXT = """\
Copyright 2014-2021 Adobe (http://www.adobe.com/), with Reserved Font Name 'Source'.
Noto is a trademark of Google Inc.

This Font Software is licensed under the SIL Open Font License, Version 1.1.
This license is copied below, and is also available with a FAQ at:
https://openfontlicense.org

The fonts in this directory are SUBSETS (Modified Versions) restricted to the
GB2312 character set plus the characters used by Xionghan Chess. Per condition 3
of the license, the family name has been changed to "Noto Sans SC Subset" /
"Noto Serif SC Subset" and does not use the Reserved Font Name.

-----------------------------------------------------------
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007
-----------------------------------------------------------

PREAMBLE
The goals of the Open Font License (OFL) are to stimulate worldwide
development of collaborative font projects, to support the font creation
efforts of academic and linguistic communities, and to provide a free and
open framework in which fonts may be shared and improved in partnership
with others.

The OFL allows the licensed fonts to be used, studied, modified and
redistributed freely as long as they are not sold by themselves. The
fonts, including any derivative works, can be bundled, embedded,
redistributed and/or sold with any software provided that any reserved
names are not used by derivative works. The fonts and derivatives,
however, cannot be released under any other type of license. The
requirement for fonts to remain under this license does not apply to any
document created using the fonts or their derivatives.

DEFINITIONS
"Font Software" refers to the set of files released by the Copyright
Holder(s) under this license and clearly marked as such. This may include
source files, build scripts and documentation.

"Reserved Font Name" refers to any names specified as such after the
copyright statement(s).

"Original Version" refers to the collection of Font Software components as
distributed by the Copyright Holder(s).

"Modified Version" refers to any derivative made by adding to, deleting,
or substituting -- in part or in whole -- any of the components of the
Original Version, by changing formats or by porting the Font Software to a
new environment.

"Author" refers to any designer, engineer, programmer, technical writer or
other person who contributed to the Font Software.

PERMISSION & CONDITIONS
Permission is hereby granted, free of charge, to any person obtaining a copy
of the Font Software, to use, study, copy, merge, embed, modify, redistribute,
and sell modified and unmodified copies of the Font Software, subject to the
following conditions:

1) Neither the Font Software nor any of its individual components, in
Original or Modified Versions, may be sold by itself.

2) Original or Modified Versions of the Font Software may be bundled,
redistributed and/or sold with any software, provided that each copy contains
the above copyright notice and this license. These can be included either as
stand-alone text files, human-readable headers or in the appropriate
machine-readable metadata fields within text or binary files as long as those
fields can be easily viewed by the user.

3) No Modified Version of the Font Software may use the Reserved Font Name(s)
unless explicit written permission is granted by the corresponding Copyright
Holder. This restriction only applies to the primary font name as presented
to the users.

4) The name(s) of the Copyright Holder(s) or the Author(s) of the Font Software
shall not be used to promote, endorse or advertise any Modified Version, except
to acknowledge the contribution(s) of the Copyright Holder(s) and the Author(s)
or with their explicit written permission.

5) The Font Software, modified or unmodified, in part or in whole, must be
distributed entirely under this license, and must not be distributed under any
other license. The requirement for fonts to remain under this license does not
apply to any document created using the Font Software.

TERMINATION
This license becomes null and void if any of the above conditions are not met.

DISCLAIMER
THE FONT SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
OR IMPLIED, INCLUDING BUT NOT LIMITED TO ANY WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT OF COPYRIGHT, PATENT,
TRADEMARK, OR OTHER RIGHT. IN NO EVENT SHALL THE COPYRIGHT HOLDER BE LIABLE
FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, INCLUDING ANY GENERAL, SPECIAL,
INDIRECT, INCIDENTAL, OR CONSEQUENTIAL DAMAGES, WHETHER IN AN ACTION OF
CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF THE USE OR INABILITY TO USE
THE FONT SOFTWARE OR FROM OTHER DEALINGS IN THE FONT SOFTWARE.
"""

# 棋子字形里不在 GB2312 的生僻字，必须显式补进子集，否则棋盘上会出现方块。
# （与 desktop/ui/theme.py 的 NAMES 对应；测试会断言二者一致。）
EXTRA_PIECE_GLYPHS = "漢俥傌相仕炮兵尉射檑甲刺楯巡汗車馬象士砲卒衛䠶礌胄碷廵"


def gb2312_charset() -> set[str]:
    """GB2312 全部字符（汉字 6763 + 标点/全角符号/希腊/俄文等）。"""
    chars: set[str] = set()
    for high in range(0xA1, 0xF8):
        for low in range(0xA1, 0xFF):
            try:
                chars.add(bytes([high, low]).decode("gb2312"))
            except UnicodeDecodeError:
                continue
    return chars


def project_charset() -> set[str]:
    """项目自有字符：源码 + 语言包 + 文本资源里出现过的所有字符。"""
    chars: set[str] = set()
    for pattern in ("src/**/*.py", "locales/**/*.json", "src/**/*.md"):
        for path in PROJECT_ROOT.glob(pattern):
            try:
                chars |= set(path.read_text(encoding="utf-8"))
            except (UnicodeDecodeError, OSError):
                continue
    return chars


def build(source_dir: Path, *, keep_full: bool = False) -> None:
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        sys.exit("需要 fonttools：python -m pip install fonttools")

    charset = gb2312_charset() | project_charset() | set(EXTRA_PIECE_GLYPHS)
    charset |= {chr(code) for code in range(0x20, 0x7F)}  # ASCII 可打印
    text = "".join(sorted(charset))
    print(f"子集字符数：{len(charset)}（GB2312 + 项目字符 + 棋子生僻字 + ASCII）")

    FONT_DIR.mkdir(parents=True, exist_ok=True)
    staging = PROJECT_ROOT / "build" / "fonts"
    staging.mkdir(parents=True, exist_ok=True)
    text_file = staging / "charset.txt"
    text_file.write_text(text, encoding="utf-8")

    total_before = total_after = 0
    for source_name, family in SUBSET_FAMILY.items():
        source = source_dir / source_name
        if not source.is_file():
            sys.exit(f"找不到源字体：{source}\n（Noto Sans/Serif SC 随 Windows 10+ 提供，或用 --source-dir 指定）")
        total_before += source.stat().st_size
        target = FONT_DIR / OUTPUT_NAME[source_name]

        result = subprocess.run(
            [
                sys.executable, "-m", "fontTools.subset", str(source),
                f"--text-file={text_file}",
                f"--output-file={target}",
                "--layout-features=*",
                "--no-hinting",
                "--desubroutinize",
                "--name-IDs=*",
                "--recalc-bounds",
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            sys.exit(f"子集化失败（{source_name}）：\n{result.stderr or result.stdout}")

        # 改 family 名（subset 工具没有直接改名参数，用 fontTools 改 name 表）
        font = TTFont(target)
        new_family, new_full = family
        for record in font["name"].names:
            if record.nameID in (1, 4, 16):  # family / full name / typographic family
                record.string = new_family
            elif record.nameID == 6:  # PostScript name
                record.string = new_full.replace(" ", "")
        font.save(target)
        font.close()

        size = target.stat().st_size
        total_after += size
        print(f"  {source_name} -> {target.name}  {size / 1e6:.2f} MB")

    (FONT_DIR / "OFL.txt").write_text(OFL_TEXT, encoding="utf-8")
    print(f"\n合计：{total_before / 1e6:.1f} MB -> {total_after / 1e6:.1f} MB"
          f"（省 {(total_before - total_after) / 1e6:.1f} MB）")
    print("许可：SIL OFL 1.1（已写 OFL.txt）")

    if keep_full:
        print("提示：--keep-full 仅用于对照，不会覆盖正式产物")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="生成随包开源字体子集（S2-4）")
    parser.add_argument(
        "--source-dir", type=Path, default=Path("C:/Windows/Fonts"),
        help="NotoSansSC-VF.ttf / NotoSerifSC-VF.ttf 所在目录",
    )
    parser.add_argument("--keep-full", action="store_true", help="同时保留完整字体用于对照")
    args = parser.parse_args(argv)
    build(args.source_dir, keep_full=args.keep_full)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
