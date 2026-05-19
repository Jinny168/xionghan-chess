"""
棋子图片生成器 - 参考主流在线象棋平台（天天象棋、腾讯象棋等）
生成所有红方和黑方棋子图片
【优化版：更大、更清晰、文字更大、修复黑射黑礌】
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 棋子配置 - 严格按照 chess-piece.js 中的定义
PIECES = {
    # 红方棋子
    'honghan': ('漢', '#d42a2a'),      # 汉王 - 鲜红色
    'hongshi': ('仕', '#d42a2a'),      # 仕
    'hongxiang': ('相', '#d42a2a'),    # 相
    'hongche': ('俥', '#d42a2a'),      # 车
    'hongma': ('傌', '#d42a2a'),       # 马
    'hongpao': ('炮', '#d42a2a'),      # 炮
    'hongbing': ('兵', '#d42a2a'),     # 兵
    'hongshe': ('射', '#d42a2a'),      # 射
    'honglei': ('檑', '#d42a2a'),      # 檑
    
    # 黑方棋子
    'heihan': ('汗', '#1a1a1a'),       # 汗王 - 深黑色
    'heishi': ('士', '#1a1a1a'),       # 士
    'heixiang': ('象', '#1a1a1a'),     # 象
    'heiche': ('車', '#1a1a1a'),       # 车
    'heima': ('馬', '#1a1a1a'),        # 马
    'heipao': ('砲', '#1a1a1a'),       # 炮
    'heibing': ('卒', '#1a1a1a'),      # 卒
    'heishe': ('䠶', '#1a1a1a'),       # '': She, '礌': Lei
    'heilei': ('礌', '#1a1a1a'),       # 礌
}

# 图片尺寸配置 - 参考主流平台，棋子更大更清晰
IMAGE_SIZE = 160        # 棋子图片尺寸（从120增加到160）
PIECE_RADIUS = 68       # 棋子半径（从50增加到68）
OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images', 'pieces')

def create_piece_base(size, radius):
    """创建棋子基础 - 3D立体效果，完全不透明"""
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2
    
    # 从外到内绘制，创建3D渐变效果
    for r in range(radius, 0, -1):
        ratio = r / radius
        
        # 浅米色木质底色
        if ratio > 0.8:
            # 边缘稍暗
            base_color = (240, 235, 225)
        elif ratio > 0.5:
            # 中间亮
            base_color = (252, 248, 238)
        else:
            # 中心稍暗
            base_color = (245, 240, 228)
        
        # 完全不透明
        color = (*base_color, 255)
        
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=color,
            outline=None
        )
    
    return img

def draw_piece_image(name, text, text_color):
    """绘制单个棋子图片 - 更大、更清晰"""
    size = IMAGE_SIZE
    radius = PIECE_RADIUS
    
    # 透明底图
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    
    center = size // 2

    # 1. 绘制棋子主体（3D木质效果）
    piece_base = create_piece_base(size, radius)
    img = Image.alpha_composite(img, piece_base)
    draw = ImageDraw.Draw(img)

    # 2. 外边框（深棕色，清晰）
    draw.ellipse(
        [center-radius, center-radius, center+radius, center+radius],
        outline=(80, 50, 20),
        width=3
    )

    # 3. 内圈装饰线
    inner_radius = radius - 8
    draw.ellipse(
        [center-inner_radius, center-inner_radius, center+inner_radius, center+inner_radius],
        outline=(180, 160, 130),
        width=2
    )

    # 4. 文字（更大、更清晰）
    try:
        # 优先使用楷体，字号更大（增加到80px）
        font = ImageFont.truetype("C:/Windows/Fonts/simkai.ttf", 80)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 76)
        except:
            font = ImageFont.load_default()

    # 文字居中
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = center - tw//2 - bbox[0]
    ty = center - th//2 - bbox[1]

    # 文字阴影（增强立体感和清晰度）
    draw.text((tx+2, ty+2), text, fill=(0, 0, 0, 80), font=font)

    # 文字颜色（更鲜艳、更清晰）
    if 'hong' in name:
        text_fill = (190, 35, 35)  # 鲜红色，比之前更亮
    else:
        text_fill = (30, 30, 30)   # 深黑色，对比度更强

    draw.text((tx, ty), text, fill=text_fill, font=font)

    # 5. 左上角高光（增强3D效果）
    highlight_radius = radius // 3
    highlight = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    
    # 椭圆形高光，更自然
    hd.ellipse(
        [center-radius+15, center-radius+15, 
         center-radius+15+highlight_radius*2, center-radius+15+highlight_radius*2],
        fill=(255, 255, 255, 60)
    )
    img = Image.alpha_composite(img, highlight)

    # 6. 底部阴影（增强立体感）
    shadow = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    shadow_offset = 4
    sd.ellipse(
        [center-radius+shadow_offset, center-radius+shadow_offset, 
         center+radius+shadow_offset, center+radius+shadow_offset],
        fill=(0, 0, 0, 40)
    )
    img = Image.alpha_composite(shadow, img)

    return img

def generate_all_pieces():
    """生成所有棋子图片"""
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f" 创建目录: {OUTPUT_DIR}")
    
    print("开始生成棋子图片（优化版：更大更清晰）...")
    print("=" * 60)
    print(f"棋子尺寸: {IMAGE_SIZE}x{IMAGE_SIZE} px")
    print(f"棋子半径: {PIECE_RADIUS} px")
    print("=" * 60)
    
    for name, (text, color) in PIECES.items():
        print(f"生成: {name} ({text})")
        piece_img = draw_piece_image(name, text, color)
        output_path = os.path.join(OUTPUT_DIR, f"{name}.png")
        piece_img.save(output_path, 'PNG')
        print(f"   保存: {output_path}")
    
    print("=" * 60)
    print(" 所有棋子图片生成完成（更大更清晰版）！")
    print(f"输出目录: {OUTPUT_DIR}")

if __name__ == '__main__':
    generate_all_pieces()
