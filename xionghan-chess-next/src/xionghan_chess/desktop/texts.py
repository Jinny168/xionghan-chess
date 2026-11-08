"""桌面端界面文案的英文对照（问题 P1-J）。

## 为什么用「中文原文」当 key

codebase 里已有 45 处 `'中文' if lang!='en' else 'English'` 的内联三元，再给
每个字符串另起一套 `desktop.xxx` 键名，只会让「代码里写了什么」和「语言包里
是什么」越离越远。这里用 gettext 的 msgid 思路：**中文原文就是键**，
英文查表替换。好处：

- 代码保持可读，改文案时不用同步改两处；
- 漏翻的字符串会原样显示中文（降级而不是崩溃），且能被
  `tests/test_desktop_i18n_keys.py` 扫出来；
- 表只有一份，审校英文时不用在源码里翻。

## 覆盖范围

只覆盖**桌面端写死的中文**。棋子字形（`theme.NAMES` 的 `漢/俥/傌…`）是棋子的
视觉本体，任何语言下都必须是中文，不在本表内。带变量的句子走 `dlf()`，
模板用 `{name}` 占位。
"""

from __future__ import annotations

# 当前界面语言。桌面端同一时刻只有一种语言，且 `apply_appearance()` 会在
# 语言变更后重建界面，所以这里用一个模块级状态而不是给每个调用点加参数。
_LANGUAGE = "zh-CN"

EN: dict[str, str] = {
    # ---- 菜单 / 主界面 ----
    "残局与排局训练": "Endgame & set-play drills",
    "翻转棋盘": "Flip board",
    "账号与云同步": "Account & cloud sync",
    "对局统计": "Statistics",
    "检查更新": "Check for updates",
    "打开自动保存目录": "Open autosave folder",
    "登场棋子配置": "Starting pieces",
    "创建局域网房间": "Create LAN room",
    "加入局域网房间": "Join LAN room",
    "观战局域网房间": "Spectate LAN room",
    "本机对局": "Local game",
    "旁观对局": "Spectate",
    "复盘": "Review",
    "当前棋局还没有棋谱": "No moves to review yet",
    "导出棋局": "Export game",
    "导入棋局": "Import game",
    "匈汉棋谱 (*.xhgame);;JSON (*.json)": "Xionghan game (*.xhgame);;JSON (*.json)",
    "匈汉棋谱 (*.xhgame *.fen *.json)": "Xionghan game (*.xhgame *.fen *.json)",
    "当前棋局.xhgame": "current-game.xhgame",
    "导出失败": "Export failed",
    "导入失败": "Import failed",
    "打开目录失败": "Could not open folder",
    "棋谱读取失败": "Could not read game file",
    "AI 异常": "AI error",
    # 箭号 ↕ 不在随包字体子集里（GB2312 之外），英文侧不要带它
    "翻转": "Flip",
    "红方": "Red",
    "黑方": "Black",
    # ---- 对局操作 ----
    "认输": "Resign",
    "确认认输并结束当前对局？": "Resign and end this game?",
    "提和": "Offer draw",
    "确认以和棋结束当前对局？": "End this game as a draw?",
    "悔棋": "Undo",
    "暂停": "Pause",
    "复活": "Resurrect",
    "当前没有可用的兵卒复活位置": "No pawn can be resurrected right now",
    "非法走棋": "Illegal move",
    "兵卒升变": "Pawn promotion",
    "选择升变棋子": "Choose promotion piece",
    "提示：": "Hint: ",
    # ---- 联机 ----
    "网络": "Network",
    "连接尚未建立": "Not connected yet",
    "聊天": "Chat",
    "聊天仅在联机房间中可用": "Chat is only available in online rooms",
    "发送快捷短语": "Quick phrases",
    "音效风格": "Sound pack",
    "经典": "Classic",
    "网页合成": "Web synth",
    "音效风格": "Sound pack",
    "经典": "Classic",
    "网页合成": "Web synth",
    "输入聊天内容": "Type a message",
    "发送": "Send",
    "房间号": "Room code",
    "观战房间": "Spectate room",
    "加入房间": "Join room",
    "观战失败": "Spectating failed",
    "网络请求失败": "Network request failed",
    "桌面玩家": "Desktop player",
    "桌面观众": "Desktop spectator",
    "玩家": "Player",
    # ---- 账号 / 云同步 ----
    "账号": "Account",
    "账号与云同步 ": "Account & cloud sync",
    "登录": "Sign in",
    "注册": "Register",
    "用户名": "Username",
    "密码": "Password",
    "账号资料": "Profile",
    "显示名称": "Display name",
    "账号头像": "Avatar",
    "默认头像": "Default avatar",
    "外部 URL": "External URL",
    "头像 URL": "Avatar URL",
    "选择头像": "Choose avatar",
    "云同步": "Cloud sync",
    "选择操作": "Choose an action",
    "退出登录": "Sign out",
    "修改资料与头像": "Edit profile & avatar",
    "上传当前棋局": "Upload current game",
    "当前棋局已上传": "Current game uploaded",
    "同步外观偏好": "Sync appearance",
    "偏好设置已同步": "Preferences synced",
    "查看云端棋谱": "View cloud games",
    "云端棋谱": "Cloud games",
    "暂无云端棋谱": "No cloud games yet",
    "已收藏": "Saved",
    "未收藏": "Not saved",
    "云同步失败": "Cloud sync failed",
    # ---- 文档 / 对话框 ----
    "规则文档": "Piece rules",
    "帮助文档": "Help",
    "关于文档": "About",
    "关闭": "Close",
    "确认": "OK",
    "打开目录": "Open folder",
    "继续对局": "Resume game",
    "本地棋谱库": "Local game library",
    "暂无本地棋谱；结束对局后将自动保存到这里": "No saved games yet; finished games are saved here automatically",
    "正在分析对局…": "Analysing game…",
    "分析失败": "Analysis failed",
    "最佳": "Best",
    "良好": "Good",
    "欠准": "Inaccuracy",
    "失误": "Mistake",
    "严重失误": "Blunder",
    # ---- 训练 / 题库 ----
    "导入题库": "Import puzzles",
    "题库导入": "Puzzle import",
    "题库导入失败": "Puzzle import failed",
    "题库文件里没有任何题目": "The puzzle file contains no puzzles",
    "再想想": "Not quite",
    "过关": "Solved",
    "训练完成，可继续自由对弈": "Training complete; free play resumed",
    # ---- 音效 ----
    "部分音效无法播放：": "Some sounds could not play: ",
    "音效加载/播放失败（文件缺失或格式不支持）": "failed to load or play (missing file or unsupported format)",
    "背景音乐加载失败": "background music failed to load",
    "音效不可用：": "Audio unavailable: ",
    # ---- 设置 ----
    "原色（无背景图片）": "Plain (no background)",
    "微软雅黑": "Microsoft YaHei",
    "楷体": "KaiTi",
    "宋体": "SimSun",
    "仿宋": "FangSong",
    # ---- 棋子图谱 ----
    "预览三风格": "Preview all styles",
    "常规棋子": "Standard pieces",
    "特色棋子": "Signature pieces",
    # 缺图格左下角的小标：这枚子当前是字形回退，不是美术
    "字": "glyph",
    # ---- 更新 ----
    "发现新版本": "Update available",
    "打开下载页": "Open download page",
    "以后再说": "Later",
    "已是最新版本": "Up to date",
    "检查更新失败": "Update check failed",
    "更新信息无法解析，请稍后再试。": "Could not read the update manifest. Please try again later.",
    "更新信息格式无法识别": "Unrecognized update manifest",
}

# 带变量的句子。中文模板即 key；英文侧用同样的 {占位符}。
TEMPLATES: dict[str, str] = {
    "棋局已保存：{path}": "Game saved: {path}",
    "已载入：{path}": "Loaded: {path}",
    "当前版本 {version}，最新版本 {latest}": "Current {version}, latest {latest}",
    "当前版本 {version} 已是最新。": "You are on the latest version ({version}).",
    "没能连上更新服务器：{detail}": "Could not reach the update server: {detail}",
    "已登录：{name}": "Signed in as {name}",
    "内置头像 {index}": "Built-in avatar {index}",
    "正解！《{title}》已解出。": "Correct — “{title}” solved.",
    "正解，继续第 {cursor}/{total} 手": "Correct — step {cursor}/{total}",
    "训练《{title}》第 {cursor}/{total} 手": "Puzzle “{title}” step {cursor}/{total}",
    "红方 {red} 枚 · 黑方 {black} 枚": "Red {red} · Black {black} pieces",
    "第 {step} 步 ·": "Move {step} ·",
    "· 损失 {loss}": "· loss {loss}",
    "文件：{path}": "File: {path}",
    "棋谱目录：{path}": "Game folder: {path}",
    "自定义题库读取失败（已忽略）：{exc}": "Could not read the custom puzzle bank (ignored): {exc}",
    "已导入 {added} 条题目{suffix}。当前自定义题库共 {total} 条。":
        "Imported {added} puzzle(s){suffix}. Custom bank now has {total}.",
    "没有新增题目（{skipped} 条 id 已存在）。": "Nothing new added ({skipped} id(s) already exist).",
    "，{skipped} 条已存在跳过": ", {skipped} skipped as duplicates",
    "自动重连失败，请重新加入房间": "Reconnect failed, please rejoin the room",
    "网络中断，正在重连": "Connection lost, reconnecting",
    "{profile} · {plies} 手": "{profile} · {plies} moves",
    "{ply}. {notation}  · {quality}  · 损失 {loss}": "{ply}. {notation}  · {quality}  · loss {loss}",
    "第 {step} / {total} 步 · {notation}": "Move {step} / {total} · {notation}",
    "背景 {index}": "Background {index}",
    "未知档位「{name}」，已回落到默认": "Unknown level “{name}” — reverted to the default",
    "{exc}\n\n文件：{path}": "{exc}\n\nFile: {path}",
    "对局结束": "Game over",
}


def set_language(language: str) -> None:
    """由界面在启动与语言变更时调用（`apply_appearance()`）。"""
    global _LANGUAGE
    _LANGUAGE = "en" if language == "en" else "zh-CN"


def current_language() -> str:
    return _LANGUAGE


def dl(text: str) -> str:
    """translate label：英文模式查表，其余原样返回。

    查不到就返回中文原文 —— 宁可显示一句中文，也不要显示空串或键名。
    """
    if _LANGUAGE != "en":
        return text
    return EN.get(text, text)


def dlf(template: str, **values: object) -> str:
    """带变量的文案。中文模板即 key，英文侧用同一组占位符。"""
    pattern = TEMPLATES.get(template, template) if _LANGUAGE == "en" else template
    try:
        return pattern.format(**values)
    except (KeyError, IndexError):
        # 占位符对不上时退回中文模板，不让界面因为一个漏填的变量崩掉
        return template.format(**values)
