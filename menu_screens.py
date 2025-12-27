import sys

import pygame

from config import (
    DEFAULT_WINDOW_WIDTH, DEFAULT_WINDOW_HEIGHT,
    BLACK, GOLD,
    MODE_PVP, MODE_PVC, CAMP_RED, CAMP_BLACK, FPS
)
from ui_elements import Button
from utils import load_font, draw_background


class ModeSelectionScreen:
    def __init__(self):
        # 初始化窗口尺寸和模式
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 模式选择")
        
        self.update_layout()
        self.selected_mode = None
        
    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        button_width = 300
        button_height = 80
        button_spacing = 40
        center_x = self.window_width // 2
        center_y = self.window_height // 2
        
        # 创建按钮
        self.pvp_button = Button(
            center_x - button_width // 2,
            center_y - button_height - button_spacing,
            button_width,
            button_height,
            "双人对战",
            32
        )
        
        self.pvc_button = Button(
            center_x - button_width // 2,
            center_y,
            button_width,
            button_height,
            "人机对战",
            32
        )
        
        self.settings_button = Button(
            center_x - button_width // 2,
            center_y + button_height + button_spacing,
            button_width,
            button_height,
            "自定义设置",
            32
        )
        
        self.rules_button = Button(
            center_x - button_width // 2,
            center_y + 2 * (button_height + button_spacing),
            button_width,
            button_height,
            "游戏规则",
            32
        )

    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            # 获取显示器信息
            info = pygame.display.Info()
            # 保存窗口模式的尺寸
            self.windowed_size = (self.window_width, self.window_height)
            # 切换到全屏模式
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            # 恢复窗口模式
            self.window_width, self.window_height = self.windowed_size
            self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        
        # 更新布局
        self.update_layout()
        
    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新布局
        self.update_layout()
        
    def run(self):
        """运行模式选择界面"""
        clock = pygame.time.Clock()
        
        while self.selected_mode is None:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.handle_resize((event.w, event.h))
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and 
                        pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.pvp_button.is_clicked(mouse_pos, event):
                        self.selected_mode = MODE_PVP
                    elif self.pvc_button.is_clicked(mouse_pos, event):
                        self.selected_mode = MODE_PVC
                    elif self.settings_button.is_clicked(mouse_pos, event):
                        self.selected_mode = "settings"
                    elif self.rules_button.is_clicked(mouse_pos, event):
                        self.selected_mode = "rules"

            
            # 更新按钮悬停状态
            self.pvp_button.check_hover(mouse_pos)
            self.pvc_button.check_hover(mouse_pos)
            self.settings_button.check_hover(mouse_pos)
            self.rules_button.check_hover(mouse_pos)

            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
        
        return self.selected_mode
    
    def draw(self):
        """绘制选择界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)
        
        # 绘制标题
        title_font = load_font(64)
        title_text = "匈汉象棋"
        title_surface = title_font.render(title_text, True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width//2, 150))
        self.screen.blit(title_surface, title_rect)
        
        # 绘制金色装饰线
        line_y = title_rect.bottom + 20
        pygame.draw.line(
            self.screen, 
            GOLD, 
            (self.window_width//4, line_y), 
            (self.window_width*3//4, line_y), 
            3
        )
        
        # 绘制副标题
        subtitle_font = load_font(36)
        subtitle_text = "请选择游戏模式"
        subtitle_surface = subtitle_font.render(subtitle_text, True, BLACK)
        subtitle_rect = subtitle_surface.get_rect(center=(self.window_width//2, line_y + 60))
        self.screen.blit(subtitle_surface, subtitle_rect)
        
        # 绘制按钮
        self.pvp_button.draw(self.screen)
        self.pvc_button.draw(self.screen)
        self.settings_button.draw(self.screen)
        self.rules_button.draw(self.screen)

        
        # 绘制按钮说明文字
        desc_font = load_font(18)
        pvp_desc = "两位玩家轮流对弈"
        pvc_desc = "与电脑AI对弈"
        settings_desc = "自定义游戏规则"
        rules_desc = "查看游戏规则和玩法说明"
        
        pvp_desc_surface = desc_font.render(pvp_desc, True, BLACK)
        pvc_desc_surface = desc_font.render(pvc_desc, True, BLACK)
        settings_desc_surface = desc_font.render(settings_desc, True, BLACK)
        rules_desc_surface = desc_font.render(rules_desc, True, BLACK)
        
        pvp_desc_rect = pvp_desc_surface.get_rect(
            center=(self.window_width//2, self.pvp_button.rect.bottom + 25)
        )
        pvc_desc_rect = pvc_desc_surface.get_rect(
            center=(self.window_width//2, self.pvc_button.rect.bottom + 25)
        )
        settings_desc_rect = settings_desc_surface.get_rect(
            center=(self.window_width//2, self.settings_button.rect.bottom + 25)
        )
        rules_desc_rect = rules_desc_surface.get_rect(
            center=(self.window_width//2, self.rules_button.rect.bottom + 25)
        )
        
        self.screen.blit(pvp_desc_surface, pvp_desc_rect)
        self.screen.blit(pvc_desc_surface, pvc_desc_rect)
        self.screen.blit(settings_desc_surface, settings_desc_rect)
        self.screen.blit(rules_desc_surface, rules_desc_rect)

        
        # 绘制版权信息
        copyright_text = "© 2025 靳中原"
        copyright_surface = desc_font.render(copyright_text, True, (128, 0, 128))
        copyright_rect = copyright_surface.get_rect(
            center=(self.window_width//2, self.window_height - 30)
        )
        self.screen.blit(copyright_surface, copyright_rect)

class RulesScreen:
    def __init__(self):
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 游戏规则")
        
        # 规则文本
        self.rules_text = [
            "匈汉象棋游戏规则：",
            "",
            "1. 棋盘：13x13格棋盘，中间为长城阴山区域",
            "2. 棋子：包括汉/汗(王)、仕(士)、相(象)、马、车、炮、兵(卒)、",
            "      尉(衛)、射(䠶)、檑(礌)、甲(胄)",
            "",
            "各棋子走法：",
            "- 将(汉/汗)：在九宫内移动，可横竖斜走，出九宫后失去斜走能力",
            "- 仕(士)：在九宫内斜走，出九宫后增加直走能力",
            "- 相(象)：走田字，无塞象眼限制，可过河，过河后增加横竖两格跳跃能力",
            "- 马：走日字，可走直线(直三走法)",
            "- 车：横竖直线移动，无距离限制",
            "- 炮：移动同车，吃子需隔一子",
            "- 兵(卒)：未过河只能前进，过河后可横移",
            "- 尉(衛)：跳跃过棋子后在碰撞前的区间内移动，与其照面的敌方棋子禁止移动和攻击",
            "- 射(䠶)：斜向移动，最多移动3格，不可越子",
            "- 檑(礌)：可攻击周围落单的敌方棋子，落单即不与同色棋子横竖相连",
            "- 甲(胄)：移动同车，落子后形成2己1敌三子连线吃敌子",
            "",
            "特殊规则：",
            "- 汉/汗进入敌方九宫直接获胜",
            "",
            "胜负判定：",
            "- 将死对方将/帅",
            "- 汉/汗进入敌方九宫",
            "- 对方将/帅被照面(违规)"
        ]
        
        # 滚动参数
        self.scroll_y = 0
        self.scroll_speed = 20
        
        # 返回按钮
        button_width = 120
        button_height = 40
        self.back_button = Button(
            self.window_width - button_width - 20, 
            20, 
            button_width, 
            button_height, 
            "返回", 
            20
        )
    
    def run(self):
        """运行规则界面"""
        clock = pygame.time.Clock()
        
        running = True
        while running:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                
                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.window_width, self.window_height = event.w, event.h
                        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
                        # 更新返回按钮位置
                        self.back_button = Button(
                            self.window_width - 120 - 20, 
                            20, 
                            120, 
                            40, 
                            "返回", 
                            20
                        )
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and 
                        pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()
                    
                    # 滚动控制
                    if event.key == pygame.K_UP:
                        self.scroll_y = min(self.scroll_y + self.scroll_speed, 0)
                    elif event.key == pygame.K_DOWN:
                        self.scroll_y = max(self.scroll_y - self.scroll_speed, 
                                          -(len(self.rules_text) * 30) + self.window_height - 100)
                
                # 处理鼠标滚轮
                if event.type == pygame.MOUSEWHEEL:
                    if event.y > 0:  # 向上滚动
                        self.scroll_y = min(self.scroll_y + self.scroll_speed, 0)
                    else:  # 向下滚动
                        self.scroll_y = max(self.scroll_y - self.scroll_speed, 
                                          -(len(self.rules_text) * 30) + self.window_height - 100)
                
                # 处理鼠标点击
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.back_button.is_clicked(mouse_pos, event):
                        running = False
                        
            # 更新按钮悬停状态
            self.back_button.check_hover(mouse_pos)
            
            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
    
    def draw(self):
        """绘制规则界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)
        
        # 绘制标题
        title_font = load_font(48)
        title_text = "游戏规则"
        title_surface = title_font.render(title_text, True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width//2, 60))
        self.screen.blit(title_surface, title_rect)
        
        # 绘制规则文本
        text_font = load_font(24)
        y_pos = 120 + self.scroll_y  # 添加滚动偏移
        
        for line in self.rules_text:
            text_surface = text_font.render(line, True, BLACK)
            self.screen.blit(text_surface, (50, y_pos))
            y_pos += 30  # 行间距
        
        # 绘制返回按钮
        self.back_button.draw(self.screen)
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            # 获取显示器信息
            info = pygame.display.Info()
            # 保存窗口模式的尺寸
            self.windowed_size = (self.window_width, self.window_height)
            # 切换到全屏模式
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            # 恢复窗口模式
            self.window_width, self.window_height = self.windowed_size
            self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        
        # 更新返回按钮位置
        button_width = 120
        button_height = 40
        self.back_button = Button(
            self.window_width - button_width - 20, 
            20, 
            button_width, 
            button_height, 
            "返回", 
            20
        )

class CampSelectionScreen:
    """阵营选择界面，让玩家选择执红方还是黑方"""
    
    def __init__(self):
        # 初始化窗口尺寸和模式
        self.window_width = DEFAULT_WINDOW_WIDTH
        self.window_height = DEFAULT_WINDOW_HEIGHT
        self.is_fullscreen = False
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 选择阵营")
        
        self.update_layout()
        self.selected_camp = None
        
    def update_layout(self):
        """根据当前窗口尺寸更新布局"""
        button_width = 300
        button_height = 80
        button_spacing = 40
        center_x = self.window_width // 2
        center_y = self.window_height // 2
        
        # 创建按钮
        self.red_button = Button(
            center_x - button_width // 2,
            center_y - button_height - button_spacing // 2,
            button_width,
            button_height,
            "执红先行",
            32
        )
        
        self.black_button = Button(
            center_x - button_width // 2,
            center_y + button_spacing // 2,
            button_width,
            button_height,
            "执黑后行",
            32
        )
    
    def toggle_fullscreen(self):
        """切换全屏模式"""
        self.is_fullscreen = not self.is_fullscreen
        
        if self.is_fullscreen:
            # 获取显示器信息
            info = pygame.display.Info()
            # 保存窗口模式的尺寸
            self.windowed_size = (self.window_width, self.window_height)
            # 切换到全屏模式
            self.screen = pygame.display.set_mode((info.current_w, info.current_h), pygame.FULLSCREEN)
            self.window_width = info.current_w
            self.window_height = info.current_h
        else:
            # 恢复窗口模式
            self.window_width, self.window_height = self.windowed_size
            self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        
        # 更新布局
        self.update_layout()
        
    def handle_resize(self, new_size):
        """处理窗口大小变化"""
        self.window_width, self.window_height = new_size
        # 更新布局
        self.update_layout()
        
    def run(self):
        """运行阵营选择界面"""
        clock = pygame.time.Clock()
        
        while self.selected_camp is None:
            mouse_pos = pygame.mouse.get_pos()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                
                # 处理窗口大小变化
                if event.type == pygame.VIDEORESIZE:
                    if not self.is_fullscreen:  # 只在窗口模式下处理大小变化
                        self.handle_resize((event.w, event.h))
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    # F11或Alt+Enter切换全屏
                    if event.key == pygame.K_F11 or (
                        event.key == pygame.K_RETURN and 
                        pygame.key.get_mods() & pygame.KMOD_ALT
                    ):
                        self.toggle_fullscreen()
                
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.red_button.is_clicked(mouse_pos, event):
                        self.selected_camp = CAMP_RED
                    elif self.black_button.is_clicked(mouse_pos, event):
                        self.selected_camp = CAMP_BLACK
            
            # 更新按钮悬停状态
            self.red_button.check_hover(mouse_pos)
            self.black_button.check_hover(mouse_pos)
            
            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(FPS)
        
        return self.selected_camp
    
    def draw(self):
        """绘制选择界面"""
        # 使用统一的背景绘制函数
        draw_background(self.screen)
        
        # 绘制标题
        title_font = load_font(48)
        title_text = "选择您的阵营"
        title_surface = title_font.render(title_text, True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width//2, 150))
        self.screen.blit(title_surface, title_rect)

        # 绘制提示文字
        hint_font = load_font(24)
        hint_text = "在匈汉象棋中，红方先行"
        hint_surface = hint_font.render(hint_text, True, BLACK)
        hint_rect = hint_surface.get_rect(center=(self.window_width//2, 200))
        self.screen.blit(hint_surface, hint_rect)
        
        # 绘制金色装饰线
        line_y = title_rect.bottom + 40
        pygame.draw.line(
            self.screen, 
            GOLD, 
            (self.window_width//4, line_y), 
            (self.window_width*3//4, line_y), 
            3
        )
        
        # 绘制按钮
        self.red_button.draw(self.screen)
        self.black_button.draw(self.screen)