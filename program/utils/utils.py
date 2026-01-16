import os
import pygame
import sys

# 字体缓存
_font_cache = {}


def load_font(size, bold=False):
    """尝试加载本地字体文件，如果失败则使用默认字体"""
    # 使用缓存键，包括size和bold状态
    cache_key = (size, bold)
    if cache_key in _font_cache:
        return _font_cache[cache_key]

    font_paths = [
        'fonts/simkai.ttf',  # 楷体
        'fonts/kaiti.ttf',  # 楷体
        'fonts/fangsong.ttf',  # 仿宋
        'fonts/simhei.ttf',  # 黑体
        'fonts/xingkai.ttf',  # 行楷
        'fonts/msyh.ttc',  # 微软雅黑
    ]

    # 尝试加载游戏资源中的字体文件，使用统一的资源路径处理
    for font_path in font_paths:
        full_path = resource_path(font_path)  # 使用统一的资源路径处理函数
        if os.path.exists(full_path):
            try:
                font = pygame.font.Font(full_path, size)
                if bold and hasattr(font, 'bold'):
                    font.bold = True
                # 缓存字体对象
                _font_cache[cache_key] = font
                return font
            except Exception as e:
                print(f"加载字体失败 {full_path}: {e}")
                continue

    # 如果没有找到资源字体，使用默认字体
    # 作为最后的备选方案，尝试直接使用本地字体文件
    fallback_fonts = ['fonts/simhei.ttf', 'fonts/simkai.ttf', 'fonts/fangsong.ttf']
    for font_path in fallback_fonts:
        try:
            full_path = resource_path(font_path)  # 使用统一的资源路径处理函数
            font = pygame.font.Font(full_path, size)
            if bold and hasattr(font, 'bold'):
                font.bold = True
            # 缓存字体对象
            _font_cache[cache_key] = font
            return font
        except Exception as e:
            print(f"加载备用字体失败 {full_path}: {e}")
            continue

    # 如果所有本地字体都加载失败，返回None表示失败
    print(f"所有字体加载失败，大小: {size}, 粗体: {bold}")
    return None


def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容PyInstaller打包后的环境"""
    try:
        # PyInstaller创建的临时文件夹存储在sys._MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        # 在开发环境下，如果相对路径找不到资源，尝试在program目录下查找
        base_path = os.path.abspath(".")
        full_path = os.path.join(base_path, relative_path)
        if os.path.exists(full_path):
            return full_path
        # 如果在根目录找不到，尝试在program子目录下查找
        program_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)
        if os.path.exists(program_path):
            return program_path
        # 默认返回根目录路径
        return full_path

    return os.path.join(base_path, relative_path)


# 音效缓存
_sound_cache = {}


def load_sound(sound_name):
    """加载音效文件，支持缓存机制
    
    Args:
        sound_name: 音效名称 ('check', 'move', 'capture', 'select', 'jiangjun_voice', 'juesha_voice', 
                     'victory', 'defeat', 'qq_victory', 'qq_defeat', 'fc_victory', 'fc_defeat')
    
    Returns:
        pygame.mixer.Sound对象，如果加载失败则返回静音音效
    """
    if sound_name in _sound_cache:
        return _sound_cache[sound_name]

    # 定义音效文件路径
    sound_paths = {
        'check': os.path.join("sounds", "check.wav"),  # 旧将军音效，纯音乐
        'move': os.path.join("sounds", "move.wav"),  # 旧走子音效
        'capture': os.path.join("sounds", "capture.wav"),  # 旧吃子音效
        'select': os.path.join("sounds", "select.wav"),  # 旧选子音效
        'jiangjun_voice': os.path.join("sounds", "jiangjun.wav"),  # 旧将军音效，女声版
        'juesha_voice': os.path.join("sounds", "juesha.wav"),  # 旧绝杀音效，女声版
        'victory': os.path.join("sounds", "fc_victory_sound.wav"),  # 默认使用fc风格的胜利音效
        'defeat': os.path.join("sounds", "fc_defeat_sound.wav"),  # 默认使用fc风格的失败音效
        'qq_victory': os.path.join("sounds", "qq_victory_sound.wav"),  # QQ风格的胜利音效
        'qq_defeat': os.path.join("sounds", "qq_defeat_sound.wav"),  # QQ风格的失败音效
        'fc_victory': os.path.join("sounds", "fc_victory_sound.wav"),  # 默认使用fc风格的胜利音效
        'fc_defeat': os.path.join("sounds", "fc_defeat_sound.wav"),  # 默认使用fc风格的失败音效
        'button': os.path.join("sounds", "button.wav"),  # 点击按钮的音效，暂未使用
        'choose': os.path.join("sounds", "choose.wav"),  # 新选子音效
        'drop': os.path.join("sounds", "drop.wav"),  # 新走子音效
        'eat': os.path.join("sounds", "eat.wav"),  # 新吃子音效
        'warn': os.path.join("sounds", "warn.wav"),  # 新将军音效
        'qq_background': os.path.join("sounds", "qq_background_sound.wav"),  # QQ风格背景音乐
        'fc_background': os.path.join("sounds", "fc_background_sound.wav")  # FC风格背景音乐
    }

    if sound_name not in sound_paths:
        print(f"未知的音效名称: {sound_name}")
        # 返回一个空的音效对象
        empty_sound = pygame.mixer.Sound(bytes(bytearray(100)))
        empty_sound.set_volume(0)
        _sound_cache[sound_name] = empty_sound
        return empty_sound

    # 实际加载音效文件
    sound_path = resource_path(sound_paths[sound_name])
    if os.path.exists(sound_path):
        try:
            sound = pygame.mixer.Sound(sound_path)
            sound.set_volume(0.7)  # 设置默认音量
            # 缓存音效对象
            _sound_cache[sound_name] = sound
            return sound
        except Exception as e:
            print(f"加载音效文件失败 {sound_path}: {e}")
            print(f"尝试使用相对路径加载...")
            # 如果resource_path失败，尝试直接使用相对路径
            try:
                sound = pygame.mixer.Sound(sound_paths[sound_name])
                sound.set_volume(0.7)
                # 缓存音效对象
                _sound_cache[sound_name] = sound
                return sound
            except Exception as e2:
                print(f"使用相对路径加载音效也失败: {e2}")
    else:
        print(f"音效文件不存在: {sound_path}")

    # 如果加载失败，返回一个空的音效对象
    empty_sound = pygame.mixer.Sound(bytes(bytearray(100)))
    empty_sound.set_volume(0)
    _sound_cache[sound_name] = empty_sound
    return empty_sound


class SoundManager:
    """音效管理器 - 从sound_manager.py迁移的功能"""

    def __init__(self):
        pygame.mixer.init()
        self.current_music_style = 'fc'
        self.music_volume = 0.5
        self.sound_volume = 0.7
        self.background_music = None

        # 预加载所有音效
        self.preload_sounds()

    def preload_sounds(self):
        """预加载所有音效"""
        sound_types = ['move', 'capture', 'select', 'check', 'jiangjun_voice', 'juesha_voice',
                       'victory', 'defeat', 'qq_victory', 'qq_defeat', 'fc_victory', 'fc_defeat',
                       'button', 'choose', 'drop', 'eat', 'warn', 'qq_background', 'fc_background']
        for sound_type in sound_types:
            load_sound(sound_type)

    def play_sound(self, sound_type):
        """播放指定类型的音效"""
        sound = load_sound(sound_type)
        if sound:
            try:
                sound.play()
            except Exception as e:
                print(f"播放音效 {sound_type} 失败: {e}")

    def toggle_music_style(self):
        """切换背景音乐风格"""
        if self.current_music_style is None or self.current_music_style == 'qq':
            self.current_music_style = 'fc'
        else:
            self.current_music_style = 'qq'

        self.play_background_music()
        return self.current_music_style

    def play_background_music(self):
        """播放当前风格的背景音乐"""
        # 根据音乐风格确定音效类型
        if self.current_music_style == 'qq':
            music_type = 'qq_background'
        else:
            music_type = 'fc_background'

        # 使用全局音效路径
        global sound_paths
        music_filepath = resource_path(sound_paths[music_type])

        # 检查背景音乐文件是否存在
        if os.path.exists(music_filepath):
            try:
                pygame.mixer.music.load(music_filepath)
                pygame.mixer.music.set_volume(self.music_volume)
                pygame.mixer.music.play(-1)  # 循环播放
            except Exception as e:
                print(f"播放背景音乐失败: {e}")
        else:
            print(f"警告: 背景音乐文件 {music_type} 不存在")

    def play_victory_sound(self):
        """播放胜利音效，根据当前音乐风格选择"""
        if self.current_music_style == 'fc':
            self.play_sound('fc_victory')
        else:
            self.play_sound('qq_victory')

    def play_defeat_sound(self):
        """播放失败音效，根据当前音乐风格选择"""
        if self.current_music_style == 'fc':
            self.play_sound('fc_defeat')
        else:
            self.play_sound('qq_defeat')

    def stop_background_music(self):
        """停止背景音乐"""
        pygame.mixer.music.stop()

    def set_music_volume(self, volume):
        """设置背景音乐音量 (0.0 到 1.0)"""
        self.music_volume = max(0.0, min(1.0, volume))
        pygame.mixer.music.set_volume(self.music_volume)

    def set_sound_volume(self, volume):
        """设置音效音量 (0.0 到 1.0)"""
        self.sound_volume = max(0.0, min(1.0, volume))
        # 更新已缓存的音效音量
        for sound_name in ['check', 'move', 'capture', 'select', 'jiangjun_voice', 'juesha_voice',
                           'victory', 'defeat', 'qq_victory', 'qq_defeat', 'fc_victory', 'fc_defeat',
                           'qq_background', 'fc_background']:
            if sound_name in _sound_cache:
                _sound_cache[sound_name].set_volume(volume)


# 背景纹理缓存
_background_texture_cache = {}


def draw_background(surface, background_color=None):
    """绘制统一的背景纹理
    
    Args:
        surface: pygame表面对象
        background_color: 背景颜色，如果为None则使用默认的BACKGROUND_COLOR
    """
    from program.config.config import BACKGROUND_COLOR as DEFAULT_BG_COLOR

    # 使用传入的背景颜色或默认背景颜色
    color = background_color if background_color is not None else DEFAULT_BG_COLOR

    surface_size = surface.get_size()
    cache_key = (surface_size, color)

    # 检查缓存中是否有对应的背景纹理
    if cache_key in _background_texture_cache:
        cached_bg = _background_texture_cache[cache_key]
        # 直接将缓存的背景绘制到目标表面上
        surface.blit(cached_bg, (0, 0))
    else:
        # 创建新的背景纹理
        bg_surface = pygame.Surface(surface_size)

        # 填充基础背景色
        bg_surface.fill(color)

        # 添加纹理效果
        for i in range(0, surface_size[0], 10):
            for j in range(0, surface_size[1], 10):
                if (i + j) % 20 == 0:
                    pygame.draw.rect(bg_surface, (230, 207, 171), (i, j, 5, 5))

        # 缓存新创建的背景纹理
        _background_texture_cache[cache_key] = bg_surface

        # 将缓存的背景绘制到目标表面上
        surface.blit(bg_surface, (0, 0))
