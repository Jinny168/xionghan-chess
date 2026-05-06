"""
棋子图片生成器 - 支持多种风格
生成传统书法、现代简约、卡通风格三种棋子
"""

from PIL import Image, ImageDraw, ImageFont
import os

# 棋子配置
PIECES = {
    # 红方棋子
    'honghan': ('漢', '#d42a2a'),
    'hongshi': ('仕', '#d42a2a'),
    'hongxiang': ('相', '#d42a2a'),
    'hongche': ('俥', '#d42a2a'),
    'hongma': ('傌', '#d42a2a'),
    'hongpao': ('炮', '#d42a2a'),
    'hongbing': ('兵', '#d42a2a'),
    'hongwei': ('尉', '#d42a2a'),
    'hongshe': ('射', '#d42a2a'),
    'honglei': ('檑', '#d42a2a'),
    'hongxun': ('巡', '#d42a2a'),
    
    # 黑方棋子
    'heihan': ('汗', '#1a1a1a'),
    'heishi': ('士', '#1a1a1a'),
    'heixiang': ('象', '#1a1a1a'),
    'heiche': ('車', '#1a1a1a'),
    'heima': ('馬', '#1a1a1a'),
    'heipao': ('砲', '#1a1a1a'),
    'heibing': ('卒', '#1a1a1a'),
    'heiwei': ('衛', '#1a1a1a'),
    'heishe': ('䠶', '#1a1a1a'),
    'heilei': ('礌', '#1a1a1a'),
    'heixun': ('廵', '#1a1a1a'),
}

# 图片尺寸配置
IMAGE_SIZE = 160
PIECE_RADIUS = 68

# 输出目录基础路径
BASE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'images', 'pieces')

def create_traditional_piece(name, text, text_color):
    """传统书法风格 - 木质纹理 + 楷体"""
    size = IMAGE_SIZE
    radius = PIECE_RADIUS
    
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = size // 2

    # 1. 木质底色（3D渐变效果）
    for r in range(radius, 0, -1):
        ratio = r / radius
        if ratio > 0.8:
            base_color = (240, 235, 225)
        elif ratio > 0.5:
            base_color = (252, 248, 238)
        else:
            base_color = (245, 240, 228)
        
        draw.ellipse(
            [center - r, center - r, center + r, center + r],
            fill=(*base_color, 255)
        )

    # 2. 外边框（深棕色）
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

    # 4. 文字（楷体）
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/simkai.ttf", 80)
    except:
        try:
            font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 76)
        except:
            font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = center - tw//2 - bbox[0]
    ty = center - th//2 - bbox[1]

    # 文字阴影
    draw.text((tx+2, ty+2), text, fill=(0, 0, 0, 80), font=font)

    # 文字颜色
    if 'hong' in name:
        text_fill = (190, 35, 35)
    else:
        text_fill = (30, 30, 30)

    draw.text((tx, ty), text, fill=text_fill, font=font)

    # 5. 左上角高光
    highlight_radius = radius // 3
    highlight = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    hd = ImageDraw.Draw(highlight)
    hd.ellipse(
        [center-radius+15, center-radius+15, 
         center-radius+15+highlight_radius*2, center-radius+15+highlight_radius*2],
        fill=(255, 255, 255, 60)
    )
    img = Image.alpha_composite(img, highlight)

    return img


def create_modern_piece(name, text, text_color):
    """现代简约风格 - 扁平化设计 + 圆角矩形"""
    size = IMAGE_SIZE
    radius = PIECE_RADIUS
    
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = size // 2

    # 1. 扁平化圆形背景
    if 'hong' in name:
        bg_color = (220, 50, 50)  # 现代红
    else:
        bg_color = (40, 40, 40)   # 现代黑
    
    # 外圈
    draw.ellipse(
        [center-radius-5, center-radius-5, center+radius+5, center+radius+5],
        fill=bg_color
    )
    
    # 内圈（白色）
    draw.ellipse(
        [center-radius, center-radius, center+radius, center+radius],
        fill=(255, 255, 255)
    )

    # 2. 文字（黑体）
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 85)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = center - tw//2 - bbox[0]
    ty = center - th//2 - bbox[1]

    # 文字颜色
    if 'hong' in name:
        text_fill = (220, 50, 50)
    else:
        text_fill = (40, 40, 40)

    draw.text((tx, ty), text, fill=text_fill, font=font)

    return img


def create_cartoon_piece(name, text, text_color):
    """卡通风格 - 可爱圆润 + 渐变色彩"""
    size = IMAGE_SIZE
    radius = PIECE_RADIUS
    
    img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    center = size // 2

    # 1. 渐变圆形背景
    if 'hong' in name:
        # 红色渐变
        for r in range(radius, 0, -1):
            ratio = r / radius
            r_val = int(255 * ratio + 200 * (1 - ratio))
            g_val = int(100 * ratio + 80 * (1 - ratio))
            b_val = int(100 * ratio + 80 * (1 - ratio))
            draw.ellipse(
                [center - r, center - r, center + r, center + r],
                fill=(r_val, g_val, b_val, 255)
            )
    else:
        # 蓝色渐变
        for r in range(radius, 0, -1):
            ratio = r / radius
            r_val = int(100 * ratio + 60 * (1 - ratio))
            g_val = int(150 * ratio + 100 * (1 - ratio))
            b_val = int(220 * ratio + 180 * (1 - ratio))
            draw.ellipse(
                [center - r, center - r, center + r, center + r],
                fill=(r_val, g_val, b_val, 255)
            )

    # 2. 白色内圈
    inner_radius = radius - 10
    draw.ellipse(
        [center-inner_radius, center-inner_radius, center+inner_radius, center+inner_radius],
        fill=(255, 255, 255)
    )

    # 3. 文字（圆润字体）
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/msyh.ttc", 80)
    except:
        font = ImageFont.load_default()

    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    tx = center - tw//2 - bbox[0]
    ty = center - th//2 - bbox[1]

    # 文字阴影
    draw.text((tx+2, ty+2), text, fill=(0, 0, 0, 60), font=font)

    # 文字颜色
    if 'hong' in name:
        text_fill = (200, 50, 50)
    else:
        text_fill = (50, 100, 180)

    draw.text((tx, ty), text, fill=text_fill, font=font)

    # 4. 可爱眼睛装饰（可选）
    # 这里可以添加更多卡通元素

    return img


def generate_pieces_by_style(style_name, style_func):
    """按风格生成所有棋子"""
    output_dir = os.path.join(BASE_DIR, style_name)
    
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        print(f"✅ 创建目录: {output_dir}")
    
    print(f"\n{'='*60}")
    print(f"开始生成 {style_name} 风格棋子...")
    print(f"{'='*60}")
    print(f"棋子尺寸: {IMAGE_SIZE}x{IMAGE_SIZE} px")
    print(f"棋子半径: {PIECE_RADIUS} px")
    print(f"输出目录: {output_dir}")
    print(f"{'='*60}\n")
    
    for name, (text, color) in PIECES.items():
        print(f"生成: {name} ({text})")
        piece_img = style_func(name, text, color)
        output_path = os.path.join(output_dir, f"{name}.png")
        piece_img.save(output_path, 'PNG')
        print(f"   ✓ 保存: {output_path}")
    
    print(f"\n{'='*60}")
    print(f"✅ {style_name} 风格棋子生成完成！")
    print(f"{'='*60}\n")


def generate_all_styles():
    """生成所有风格的棋子"""
    styles = {
        'traditional': create_traditional_piece,
        'modern': create_modern_piece,
        'cartoon': create_cartoon_piece,
    }
    
    print("🎨 开始生成所有风格的棋子图片...")
    print(f"基础目录: {BASE_DIR}\n")
    
    for style_name, style_func in styles.items():
        generate_pieces_by_style(style_name, style_func)
    
    print("\n🎉 所有风格棋子生成完成！")
    print(f"\n生成的文件夹：")
    for style_name in styles.keys():
        print(f"  - {BASE_DIR}/{style_name}/")


if __name__ == '__main__':
    generate_all_styles()
