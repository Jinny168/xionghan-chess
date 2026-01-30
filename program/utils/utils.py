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
        'assets/fonts/simkai.ttf',  # 楷体
        'assets/fonts/kaiti.ttf',  # 楷体
        'assets/fonts/fangsong.ttf',  # 仿宋
        'assets/fonts/simhei.ttf',  # 黑体
        'assets/fonts/xingkai.ttf',  # 行楷
        'assets/fonts/msyh.ttc',  # 微软雅黑
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
    fallback_fonts = ['assets/fonts/simhei.ttf', 'assets/fonts/simkai.ttf', 'assets/fonts/fangsong.ttf']
    for font_path in fallback_fonts:
        full_path = resource_path(font_path)  # 使用统一的资源路径处理函数
        try:
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
        base_path = getattr(sys, '_MEIPASS', None)
        if base_path is None:
            raise AttributeError
    except AttributeError:
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

# 背景纹理缓存
_background_texture_cache = {}


def draw_background(surface, background_color=None):
    """绘制统一的背景纹理
    
    Args:
        surface: pygame表面对象
        background_color: 背景颜色，如果为None则使用默认的BACKGROUND_COLOR
    """
    from program.controllers.game_config_manager import BACKGROUND_COLOR as DEFAULT_BG_COLOR

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


def virtual_move(pieces, piece, to_row, to_col, check_function, *args):
    """ 虚拟移动棋子并执行检查函数
    
    Args:
        pieces: 棋子列表
        piece: 要移动的棋子
        to_row: 目标行
        to_col: 目标列
        check_function: 检查函数
        *args: 传递给检查函数的额外参数
        
    Returns:
        检查函数的返回值
    """
    # 保存原始位置和目标位置的棋子
    original_row, original_col = piece.row, piece.col
    target_piece = None
    
    # 查找并移除目标位置的棋子（如果存在）
    for p in pieces[:]:  # 使用切片副本以安全地修改列表
        if p.row == to_row and p.col == to_col:
            target_piece = p
            pieces.remove(p)
            break
    
    # 移动棋子到目标位置
    piece.row, piece.col = to_row, to_col
    
    # 执行检查函数
    result = check_function(pieces, *args)
    
    # 恢复棋子到原始位置
    piece.row, piece.col = original_row, original_col
    
    # 如果目标位置原本有棋子，将其放回
    if target_piece:
        target_piece.row, target_piece.col = to_row, to_col
        pieces.append(target_piece)
    
    return result


def print_board(pieces, step=None, show_step=True):
    """ 打印当前棋盘状态
    
    Args:
        pieces: 棋子列表
        step: 步数计数器，默认为[0]
        show_step: 是否显示步数，默认为True
    """
    if step is None:
        step = [0]
    if show_step:
        step[0] += 1
        print('\033[36mSTEP\033[0m:', step[0])
    
    # 创建棋盘表示
    board = [[None for _ in range(13)] for _ in range(13)]
    
    # 将棋子放置到棋盘上
    for piece in pieces:
        board[piece.row][piece.col] = piece
    
    # 打印棋盘
    for row in board:
        for cell in row:
            if cell is None:
                print('〇', end='')
            else:
                # 获取棋子名称，确保安全访问
                cell_name = getattr(cell, 'name', None)
                if cell_name and cell_name in '漢仕相傌俥炮兵巡射檑甲楯射刺尉':
                    print(f'\033[32m{cell_name}\033[0m', end='')
                elif cell_name:  # 如果有名称但不在上述列表中
                    print(f'\033[31m{cell_name}\033[0m', end='')
                else:  # 如果没有名称属性或名称为空
                    print('?', end='')  # 显示问号作为占位符
        print()
    print()


