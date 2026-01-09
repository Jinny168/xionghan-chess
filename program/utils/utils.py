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
        'fonts/simkai.ttf',      # 楷体
        'fonts/kaiti.ttf',       # 楷体
        'fonts/fangsong.ttf',    # 仿宋
        'fonts/simhei.ttf',      # 黑体
        'fonts/xingkai.ttf',     # 行楷
        'fonts/msyh.ttc',        # 微软雅黑
    ]
    
    # 尝试加载游戏资源中的字体文件
    for font_path in font_paths:
        full_path = os.path.join(os.path.dirname(__file__), font_path)
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
            font = pygame.font.Font(font_path, size)
            if bold and hasattr(font, 'bold'):
                font.bold = True
            # 缓存字体对象
            _font_cache[cache_key] = font
            return font
        except Exception as e:
            print(f"加载备用字体失败 {font_path}: {e}")
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
        base_path = os.path.abspath(".")  # 使用当前目录而非上级目录

    return os.path.join(base_path, relative_path)


# 音效缓存
_sound_cache = {}

def load_sound(sound_name):
    """加载音效文件，支持缓存机制
    
    Args:
        sound_name: 音效名称 ('check', 'move', 'capture')
    
    Returns:
        pygame.mixer.Sound对象，如果加载失败则返回静音音效
    """
    if sound_name in _sound_cache:
        return _sound_cache[sound_name]
    
    # 定义音效文件路径
    sound_paths = {
        'check': os.path.join("sounds", "check.wav"),
        'move': os.path.join("sounds", "move.wav"),
        'capture': os.path.join("sounds", "capture.wav")
    }
    
    if sound_name not in sound_paths:
        print(f"未知的音效名称: {sound_name}")
        # 返回一个空的音效对象
        empty_sound = pygame.mixer.Sound(bytes(bytearray(100)))
        empty_sound.set_volume(0)
        _sound_cache[sound_name] = empty_sound
        return empty_sound
    
    try:
        # 构建完整路径并加载音效
        sound_path = resource_path(sound_paths[sound_name])
        sound = pygame.mixer.Sound(sound_path)
        
        # 根据音效类型设置不同的音量
        if sound_name == 'check':
            sound.set_volume(0.8)  # 将军音效音量设为80%
        elif sound_name == 'move':
            sound.set_volume(0.6)  # 移动音效音量设为60%
        elif sound_name == 'capture':
            sound.set_volume(0.7)  # 吃子音效音量设为70%
        
        # 缓存音效对象
        _sound_cache[sound_name] = sound
        return sound
    except Exception as e:
        print(f"警告：未能加载音效文件 {sound_paths[sound_name]}。错误: {e}")
        # 如果加载失败，创建一个静音的音效对象
        empty_sound = pygame.mixer.Sound(bytes(bytearray(100)))
        empty_sound.set_volume(0)
        _sound_cache[sound_name] = empty_sound
        return empty_sound


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