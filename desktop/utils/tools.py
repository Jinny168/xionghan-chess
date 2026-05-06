"""工具函数模块，包含导入导出棋局和复盘等功能"""
from desktop.core.chess_pieces import (
    Ma, Xiang, Shi, Pawn, Wei, She
)

"""通用的设置界面分类绘制函数"""

import os
import sys

import pygame

from desktop.controllers.game_config_manager import game_config

# 字体缓存
_font_cache = {}

def draw_category(screen, category_background_color, category_border_color, category_padding,
                  category_title_height, category_title_font, checkbox_size, scroll_y,
                  window_width, option_font, desc_font, draw_piece_icon,
                  piece_display_char, piece_display_name, items, y_position=0):
    """
    通用的棋子分类绘制函数

    Args:
        screen: pygame屏幕对象
        category_background_color: 分类背景色
        category_border_color: 分类边框色
        category_padding: 分类内边距
        category_title_height: 分类标题高度
        category_title_font: 分类标题字体
        checkbox_size: 复选框大小
        scroll_y: 当前滚动位置
        window_width: 窗口宽度
        option_font: 选项字体
        desc_font: 描述字体
        draw_piece_icon: 绘制棋子图标的函数
        piece_display_char: 棋子显示字符
        piece_display_name: 棋子显示名称
        items: 选项列表，每个元素包含 (checkbox, label, value, text, desc, is_disabled)
        y_position: 分类在内容中的Y位置
    """
    # 计算分类区域的尺寸
    category_width = window_width - 100  # 留出边距
    items_count = len(items)  # 该分类下的设置项数量
    category_height = items_count * 60 + category_title_height + 2 * category_padding  # 包含标题高度和内边距

    # 绘制分类背景
    # 使用分类的实际位置减去滚动偏移来确定显示位置
    category_rect = pygame.Rect(50, y_position - scroll_y - category_padding, category_width, category_height)
    pygame.draw.rect(screen, category_background_color, category_rect)
    pygame.draw.rect(screen, category_border_color, category_rect, 2)

    # 绘制分类标题和图标 - 更紧密的组合
    title_y = y_position - scroll_y  # 考虑滚动偏移
    icon_x = 65
    icon_y = title_y + category_title_height // 2
    title_text_x = 90

    # 绘制图标
    draw_piece_icon(piece_display_char, icon_x, icon_y)
    # 绘制标题文字
    title_surface = category_title_font.render(piece_display_name, True, (0, 0, 0))
    screen.blit(title_surface, (title_text_x, title_y))

    # 在标题下方添加一条分割线，增强视觉分组
    separator_y = title_y + category_title_height - 2
    pygame.draw.line(screen, (180, 180, 180), (category_rect.left + 5, separator_y),
                     (category_rect.right - 5, separator_y), 1)

    # 绘制分类内容
    item_y = title_y + category_title_height + category_padding

    for index, item in enumerate(items):
        checkbox, label, value, text, desc, is_disabled = item

        # 绘制每项的背景框，形成更强的视觉分组
        item_rect = pygame.Rect(category_rect.left + 10, item_y - 5, category_rect.width - 20, 55)
        item_bg_color = (245, 245, 245) if is_disabled else (250, 250, 250)
        pygame.draw.rect(screen, item_bg_color, item_rect, border_radius=5)
        pygame.draw.rect(screen, (200, 200, 200), item_rect, 1, border_radius=5)

        # 计算复选框位置 - 确保复选框在背景框内
        checkbox_x = item_rect.left + 10  # 在背景框内留出一些边距
        checkbox_y = item_rect.top + (item_rect.height - checkbox_size) // 2  # 垂直居中
        adjusted_checkbox = pygame.Rect(
            checkbox_x,
            checkbox_y,
            checkbox_size,
            checkbox_size
        )

        if is_disabled:
            pygame.draw.rect(screen, (150, 150, 150), adjusted_checkbox, 2)  # 灰色边框
            if True:  # 对于禁用的复选框，使用固定的值（通常是True）
                pygame.draw.line(screen, (100, 100, 100),
                                 (adjusted_checkbox.left + 4, adjusted_checkbox.centery),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4), 2)
                pygame.draw.line(screen, (100, 100, 100),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4),
                                 (adjusted_checkbox.right - 4, adjusted_checkbox.top + 4), 2)
        else:
            pygame.draw.rect(screen, (0, 0, 0), adjusted_checkbox, 2)
            if value:
                pygame.draw.line(screen, (0, 0, 0),
                                 (adjusted_checkbox.left + 4, adjusted_checkbox.centery),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4), 2)
                pygame.draw.line(screen, (0, 0, 0),
                                 (adjusted_checkbox.centerx - 2, adjusted_checkbox.bottom - 4),
                                 (adjusted_checkbox.right - 4, adjusted_checkbox.top + 4), 2)

        # 绘制标签（主标题）
        # 标签位置基于复选框调整，确保在背景框内
        label_x = adjusted_checkbox.right + 5
        # 确保标签文本垂直居中对齐
        label_y = item_rect.top + (item_rect.height - option_font.get_height()) // 2
        label_color = (100, 100, 100) if is_disabled else (0, 0, 0)
        label_surface = option_font.render(text, True, label_color)
        screen.blit(label_surface, (label_x, label_y))

        # 绘制描述（辅助说明）
        desc_x = label_x
        desc_y = label_y + option_font.get_height() + 2
        # 确保描述不超出背景框范围
        if desc_y + desc_font.get_height() <= item_rect.bottom:
            desc_color = (150, 150, 150) if is_disabled else (100, 100, 100)
            desc_surface = desc_font.render(desc, True, desc_color)
            screen.blit(desc_surface, (desc_x, desc_y))

        # 添加一个小的连接线，表明复选框和标签的关联
        checkbox_right = adjusted_checkbox.right + 2
        label_left = label_x - 2
        line_start_y = label_y + label_surface.get_height() // 2
        line_end_y = line_start_y
        pygame.draw.line(screen, (200, 200, 200), (checkbox_right, line_start_y), (label_left, line_end_y), 1)

        item_y += 60

    return category_height
def toggle_fullscreen(window_width, window_height, is_fullscreen, windowed_size=None):
    """
    切换全屏模式的通用函数
    
    Args:
        window_width: 当前窗口宽度
        window_height: 当前窗口高度
        is_fullscreen: 是否为全屏模式
        windowed_size: 存储窗口模式尺寸的元组，格式为(width, height)，如果为None则创建新元组
    
    Returns:
        tuple: (new_screen, new_window_width, new_window_height, new_is_fullscreen, new_windowed_size)
               返回更新后的屏幕对象、窗口宽高、全屏状态和窗口尺寸
    """
    if windowed_size is None:
        windowed_size = (window_width, window_height)
    
    new_is_fullscreen = not is_fullscreen
    
    if new_is_fullscreen:
        # 获取显示器信息
        info = pygame.display.Info()
        # 保存窗口模式的尺寸
        new_windowed_size = (window_width, window_height)
        # 切换到全屏模式
        new_screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
        new_window_width = info.current_w
        new_window_height = info.current_h
    else:
        # 恢复窗口模式
        new_window_width, new_window_height = windowed_size
        new_screen = pygame.display.set_mode((new_window_width, new_window_height), pygame.RESIZABLE)
        new_windowed_size = windowed_size
    
    return new_screen, new_window_width, new_window_height, new_is_fullscreen, new_windowed_size

def generate_move_notation(piece, from_row, from_col, to_row, to_col):
    """生成走法的中文表示，如“炮二平五”、“马8进7”等"""
    
    # 安全检查：确保piece不为None
    if piece is None:
        return "未知走法"

    piece_name = piece.name  # 直接使用棋子名称

    # 转换列数为中文数字或数字 - 从右至左标识
    # 红方用汉字“一”至“十三”标识，黑方用数字“1”-“13”标识
    col_names_red = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二", "十三"]
    col_names_black = ["1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13"]

    # 根据棋子颜色选择合适列名表示
    col_names = col_names_red if piece.color == "red" else col_names_black

    # 计算棋盘坐标到列标识的映射（从右到左）
    col_index = 12 - from_col  # 从右到左映射 (0-12 -> 12-0)
    from_col_name = col_names[col_index]

    # 判断移动方向
    if to_row < from_row:  # 向上移动
        direction = "进" if piece.color == "red" else "退"
    elif to_row > from_row:  # 向下移动
        direction = "退" if piece.color == "red" else "进"
    else:  # 水平移动
        direction = "平"

    # 获取目标位置
    if direction == "平":
        # 平移表示目标列
        to_col_index = 12 - to_col  # 从右到左映射
        to_col_name = col_names[to_col_index]
        notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
    else:
        # 进退表示移动的距离或目标列
        # 检查是否是马、象、士或新增的对角线移动棋子
        is_diagonal_piece = (isinstance(piece, Ma) or isinstance(piece, Xiang) or
                             isinstance(piece, Shi) or isinstance(piece, She) or
                             isinstance(piece, Wei))

        if is_diagonal_piece:
            # 马、象、士、射、尉用目标列表示
            to_col_index = 12 - to_col  # 从右到左映射
            to_col_name = col_names[to_col_index]
            notation = f"{piece_name}{from_col_name}{direction}{to_col_name}"
        else:
            # 其他棋子用移动距离表示
            distance = abs(from_row - to_row)
            # 确保距离在有效范围内
            if distance < 1:
                distance = 1
            elif distance > 12:  # 最大可能距离是12格（从第0行到第12行）
                distance = 12

            if piece.color == "black" and direction == "进":
                # 黑方前进和红方后退是增加行号
                # 确保索引在有效范围内
                index = min(distance - 1, len(col_names_black) - 1)
                distance_str = col_names_black[index]
            elif piece.color == "black" and direction == "退":
                # 黑方后退和红方前进是减少行号
                # 确保索引在有效范围内
                index = min(distance - 1, len(col_names_black) - 1)
                distance_str = col_names_black[index]
            else:
                # 红方使用汉字数字表示距离
                # 确保索引在有效范围内
                # 扩展红方距离表示以适应13x13棋盘
                red_distance_names = ["一", "二", "三", "四", "五", "六", "七", "八", "九", "十", "十一", "十二"]
                index = min(distance - 1, len(red_distance_names) - 1)
                distance_str = red_distance_names[index]
            notation = f"{piece_name}{from_col_name}{direction}{distance_str}"

    return notation

def get_valid_moves(game_state, color):
    """获取指定颜色棋子的所有有效走法"""
    valid_moves = []

    for piece in game_state.pieces:
        if piece.color == color:
            # 获取该棋子所有可能的移动位置
            possible_moves, _ = game_state.calculate_possible_moves(piece.row, piece.col)

            # 添加到有效走法列表
            for to_row, to_col in possible_moves:
                valid_moves.append(((piece.row, piece.col), (to_row, to_col)))

    return valid_moves

def is_pawn_at_opponent_base(piece, to_row):
    """检查兵/卒是否移动到对方底线

    Args:
        piece: 棋子对象
        to_row: 目标行

    Returns:
        bool: 是否到达对方底线
    """
    if not isinstance(piece, Pawn):
        return False

    # 红方兵到达第0行（黑方底线），黑方卒到达第12行（红方底线）
    if piece.color == "red" and to_row == 0:
        return True
    elif piece.color == "black" and to_row == 12:
        return True

    return False





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
    from desktop.controllers.game_config_manager import BACKGROUND_COLOR as DEFAULT_BG_COLOR

    # 使用传入的背景颜色或默认背景颜色
    color = background_color if background_color is not None else DEFAULT_BG_COLOR

    surface_size = surface.get_size()
    # Convert color to tuple if it's a list to make it hashable for cache key
    cache_key = (surface_size, tuple(color) if isinstance(color, list) else color)

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


def draw_gradient_background(surface):
    """绘制渐变背景

    Args:
        surface: pygame表面对象
    """
    width, height = surface.get_size()

    # 创建渐变背景
    for y in range(height):
        # 计算渐变比例 (0.0-1.0)
        ratio = y / height

        # 定义渐变颜色 (从浅蓝到浅紫)
        r = int(135 + (230 - 135) * ratio)  # 从RGB(135,206,235)到RGB(230,230,250)
        g = int(206 + (230 - 206) * ratio)
        b = int(235 + (250 - 235) * ratio)

        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))


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

    # 根据GameRules的设置确定棋盘尺寸
    if game_config.get_setting("traditional_mode", False):
        # 传统中国象棋：9列 x 10行
        board = [[None for _ in range(9)] for _ in range(10)]
    else:
        # 匈汉象棋：13列 x 13行
        board = [[None for _ in range(13)] for _ in range(13)]

    # 将棋子放置到棋盘上
    for piece in pieces:
        # 检查棋子位置是否在当前棋盘范围内
        if 0 <= piece.row < len(board) and 0 <= piece.col < len(board[0]):
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


def is_position_on_board(row, col):
    """检查位置是否在棋盘范围内

    Args:
        row (int): 行坐标
        col (int): 列坐标

    Returns:
        bool: 位置是否在棋盘范围内
    """
    if game_config.get_setting("traditional_mode", False):
        # 传统中国象棋：9列 x 10行 (0-8列, 0-9行)
        return 0 <= row < 10 and 0 <= col < 9
    else:
        # 匈汉象棋：13列 x 13行 (0-12列, 0-12行)
        return 0 <= row < 13 and 0 <= col < 13
