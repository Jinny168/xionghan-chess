import pygame
from ui_elements import Button
from utils import load_font
from config import game_config

# 颜色定义
BLACK = (0, 0, 0)
RED = (180, 30, 30)
WHITE = (255, 255, 255)
BUTTON_COLOR = (100, 100, 200)
BUTTON_HOVER = (120, 120, 220)
BUTTON_TEXT = (240, 240, 255)
BACKGROUND_COLOR = (240, 217, 181)

class SettingsScreen:
    """自定义设置界面"""
    def __init__(self):
        self.window_width = 850
        self.window_height = 850
        self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
        pygame.display.set_caption("匈汉象棋 - 自定义设置")
        
        # 从全局配置中加载设置
        self.load_settings()
        
        # 创建界面元素
        self.create_ui_elements()
    
    def load_settings(self):
        """从全局配置加载设置"""
        self.king_can_leave_palace = game_config.get_setting("king_can_leave_palace", True)
        self.king_lose_diagonal_outside_palace = game_config.get_setting("king_lose_diagonal_outside_palace", True)
        self.king_can_diagonal_in_palace = game_config.get_setting("king_can_diagonal_in_palace", True)
        self.shi_can_leave_palace = game_config.get_setting("shi_can_leave_palace", True)
        self.shi_gain_straight_outside_palace = game_config.get_setting("shi_gain_straight_outside_palace", True)
        self.xiang_can_cross_river = game_config.get_setting("xiang_can_cross_river", True)
        self.xiang_gain_jump_two_outside_river = game_config.get_setting("xiang_gain_jump_two_outside_river", True)
        self.ma_can_straight_three = game_config.get_setting("ma_can_straight_three", True)
    
    def create_ui_elements(self):
        """创建界面元素"""
        # 标题字体
        self.title_font = load_font(48)
        self.option_font = load_font(24)
        self.desc_font = load_font(18)
        
        # 选项复选框位置
        y_start = 150
        spacing = 80
        
        # 汉/汗是否可以出九宫选项
        self.king_palace_checkbox = pygame.Rect(100, y_start, 20, 20)
        self.king_palace_label = (130, y_start)
        
        # 汉/汗出九宫后是否失去斜走能力选项
        self.king_diagonal_checkbox = pygame.Rect(100, y_start + spacing, 20, 20)
        self.king_diagonal_label = (130, y_start + spacing)
        
        # 汉/汗在九宫内是否可以斜走选项
        self.king_diagonal_in_palace_checkbox = pygame.Rect(100, y_start + 2 * spacing, 20, 20)
        self.king_diagonal_in_palace_label = (130, y_start + 2 * spacing)
        
        # 士是否可以出九宫选项
        self.shi_palace_checkbox = pygame.Rect(100, y_start + 3 * spacing, 20, 20)
        self.shi_palace_label = (130, y_start + 3 * spacing)
        
        # 士出九宫后是否获得直走能力选项
        self.shi_straight_checkbox = pygame.Rect(100, y_start + 4 * spacing, 20, 20)
        self.shi_straight_label = (130, y_start + 4 * spacing)
        
        # 相是否可以过河选项
        self.xiang_cross_checkbox = pygame.Rect(100, y_start + 5 * spacing, 20, 20)
        self.xiang_cross_label = (130, y_start + 5 * spacing)
        
        # 相过河后是否获得隔两格吃子能力选项
        self.xiang_jump_checkbox = pygame.Rect(100, y_start + 6 * spacing, 20, 20)
        self.xiang_jump_label = (130, y_start + 6 * spacing)
        
        # 马是否可以获得直走三格的能力选项
        self.ma_straight_checkbox = pygame.Rect(100, y_start + 7 * spacing, 20, 20)
        self.ma_straight_label = (130, y_start + 7 * spacing)
        
        # 按钮
        button_width = 120
        button_height = 50
        button_spacing = 20
        
        # 确认按钮
        self.confirm_button = Button(
            self.window_width // 2 - button_width - button_spacing // 2,
            y_start + 8 * spacing + 50,
            button_width,
            button_height,
            "确认",
            24
        )
        
        # 返回按钮
        self.back_button = Button(
            self.window_width // 2 + button_spacing // 2,
            y_start + 8 * spacing + 50,
            button_width,
            button_height,
            "返回",
            24
        )
    
    def draw(self):
        """绘制设置界面"""
        # 绘制背景
        self.screen.fill(BACKGROUND_COLOR)
        
        # 绘制标题
        title_surface = self.title_font.render("自定义设置", True, BLACK)
        title_rect = title_surface.get_rect(center=(self.window_width // 2, 80))
        self.screen.blit(title_surface, title_rect)
        
        # 绘制选项
        # 汉/汗是否可以出九宫
        pygame.draw.rect(self.screen, BLACK, self.king_palace_checkbox, 2)
        if self.king_can_leave_palace:
            pygame.draw.line(self.screen, BLACK, 
                           (self.king_palace_checkbox.left, self.king_palace_checkbox.top),
                           (self.king_palace_checkbox.right, self.king_palace_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.king_palace_checkbox.right, self.king_palace_checkbox.top),
                           (self.king_palace_checkbox.left, self.king_palace_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("汉/汗可以出九宫", True, BLACK)
        self.screen.blit(label_surface, self.king_palace_label)
        
        desc_surface = self.desc_font.render("允许汉/汗走出九宫区域", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.king_palace_label[0], self.king_palace_label[1] + 30))
        
        # 汉/汗出九宫后是否失去斜走能力
        pygame.draw.rect(self.screen, BLACK, self.king_diagonal_checkbox, 2)
        if self.king_lose_diagonal_outside_palace:
            pygame.draw.line(self.screen, BLACK, 
                           (self.king_diagonal_checkbox.left, self.king_diagonal_checkbox.top),
                           (self.king_diagonal_checkbox.right, self.king_diagonal_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.king_diagonal_checkbox.right, self.king_diagonal_checkbox.top),
                           (self.king_diagonal_checkbox.left, self.king_diagonal_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("汉/汗出九宫后失去斜走能力", True, BLACK)
        self.screen.blit(label_surface, self.king_diagonal_label)
        
        desc_surface = self.desc_font.render("汉/汗走出九宫后只能横竖走，不能斜走", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.king_diagonal_label[0], self.king_diagonal_label[1] + 30))
        
        # 汉/汗在九宫内是否可以斜走
        pygame.draw.rect(self.screen, BLACK, self.king_diagonal_in_palace_checkbox, 2)
        if self.king_can_diagonal_in_palace:
            pygame.draw.line(self.screen, BLACK, 
                           (self.king_diagonal_in_palace_checkbox.left, self.king_diagonal_in_palace_checkbox.top),
                           (self.king_diagonal_in_palace_checkbox.right, self.king_diagonal_in_palace_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.king_diagonal_in_palace_checkbox.right, self.king_diagonal_in_palace_checkbox.top),
                           (self.king_diagonal_in_palace_checkbox.left, self.king_diagonal_in_palace_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("汉/汗在九宫内可以斜走", True, BLACK)
        self.screen.blit(label_surface, self.king_diagonal_in_palace_label)
        
        desc_surface = self.desc_font.render("汉/汗在九宫内允许斜向移动", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.king_diagonal_in_palace_label[0], self.king_diagonal_in_palace_label[1] + 30))
        
        # 士是否可以出九宫
        pygame.draw.rect(self.screen, BLACK, self.shi_palace_checkbox, 2)
        if self.shi_can_leave_palace:
            pygame.draw.line(self.screen, BLACK, 
                           (self.shi_palace_checkbox.left, self.shi_palace_checkbox.top),
                           (self.shi_palace_checkbox.right, self.shi_palace_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.shi_palace_checkbox.right, self.shi_palace_checkbox.top),
                           (self.shi_palace_checkbox.left, self.shi_palace_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("士可以出九宫", True, BLACK)
        self.screen.blit(label_surface, self.shi_palace_label)
        
        desc_surface = self.desc_font.render("允许士走出九宫区域", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.shi_palace_label[0], self.shi_palace_label[1] + 30))
        
        # 士出九宫后是否获得直走能力
        pygame.draw.rect(self.screen, BLACK, self.shi_straight_checkbox, 2)
        if self.shi_gain_straight_outside_palace:
            pygame.draw.line(self.screen, BLACK, 
                           (self.shi_straight_checkbox.left, self.shi_straight_checkbox.top),
                           (self.shi_straight_checkbox.right, self.shi_straight_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.shi_straight_checkbox.right, self.shi_straight_checkbox.top),
                           (self.shi_straight_checkbox.left, self.shi_straight_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("士出九宫后获得直走能力", True, BLACK)
        self.screen.blit(label_surface, self.shi_straight_label)
        
        desc_surface = self.desc_font.render("士走出九宫后可以横竖移动", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.shi_straight_label[0], self.shi_straight_label[1] + 30))
        
        # 相是否可以过河
        pygame.draw.rect(self.screen, BLACK, self.xiang_cross_checkbox, 2)
        if self.xiang_can_cross_river:
            pygame.draw.line(self.screen, BLACK, 
                           (self.xiang_cross_checkbox.left, self.xiang_cross_checkbox.top),
                           (self.xiang_cross_checkbox.right, self.xiang_cross_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.xiang_cross_checkbox.right, self.xiang_cross_checkbox.top),
                           (self.xiang_cross_checkbox.left, self.xiang_cross_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("相可以过河", True, BLACK)
        self.screen.blit(label_surface, self.xiang_cross_label)
        
        desc_surface = self.desc_font.render("允许相跨越楚河汉界", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.xiang_cross_label[0], self.xiang_cross_label[1] + 30))
        
        # 相过河后是否获得隔两格吃子能力
        pygame.draw.rect(self.screen, BLACK, self.xiang_jump_checkbox, 2)
        if self.xiang_gain_jump_two_outside_river:
            pygame.draw.line(self.screen, BLACK, 
                           (self.xiang_jump_checkbox.left, self.xiang_jump_checkbox.top),
                           (self.xiang_jump_checkbox.right, self.xiang_jump_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.xiang_jump_checkbox.right, self.xiang_jump_checkbox.top),
                           (self.xiang_jump_checkbox.left, self.xiang_jump_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("相过河后获得隔两格吃子能力", True, BLACK)
        self.screen.blit(label_surface, self.xiang_jump_label)
        
        desc_surface = self.desc_font.render("相过河后可横竖方向隔一格吃子", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.xiang_jump_label[0], self.xiang_jump_label[1] + 30))
        
        # 马是否可以获得直走三格的能力
        pygame.draw.rect(self.screen, BLACK, self.ma_straight_checkbox, 2)
        if self.ma_can_straight_three:
            pygame.draw.line(self.screen, BLACK, 
                           (self.ma_straight_checkbox.left, self.ma_straight_checkbox.top),
                           (self.ma_straight_checkbox.right, self.ma_straight_checkbox.bottom), 2)
            pygame.draw.line(self.screen, BLACK,
                           (self.ma_straight_checkbox.right, self.ma_straight_checkbox.top),
                           (self.ma_straight_checkbox.left, self.ma_straight_checkbox.bottom), 2)
        
        label_surface = self.option_font.render("马可以获得直走三格的能力", True, BLACK)
        self.screen.blit(label_surface, self.ma_straight_label)
        
        desc_surface = self.desc_font.render("马可以横竖方向走三格", True, (100, 100, 100))
        self.screen.blit(desc_surface, (self.ma_straight_label[0], self.ma_straight_label[1] + 30))
        
        # 绘制按钮
        self.confirm_button.draw(self.screen)
        self.back_button.draw(self.screen)
    
    def handle_event(self, event, mouse_pos):
        """处理事件"""
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查复选框点击
            if self.king_palace_checkbox.collidepoint(mouse_pos):
                self.king_can_leave_palace = not self.king_can_leave_palace
            elif self.king_diagonal_checkbox.collidepoint(mouse_pos):
                self.king_lose_diagonal_outside_palace = not self.king_lose_diagonal_outside_palace
            elif self.king_diagonal_in_palace_checkbox.collidepoint(mouse_pos):
                self.king_can_diagonal_in_palace = not self.king_can_diagonal_in_palace
            elif self.shi_palace_checkbox.collidepoint(mouse_pos):
                self.shi_can_leave_palace = not self.shi_can_leave_palace
            elif self.shi_straight_checkbox.collidepoint(mouse_pos):
                self.shi_gain_straight_outside_palace = not self.shi_gain_straight_outside_palace
            elif self.xiang_cross_checkbox.collidepoint(mouse_pos):
                self.xiang_can_cross_river = not self.xiang_can_cross_river
            elif self.xiang_jump_checkbox.collidepoint(mouse_pos):
                self.xiang_gain_jump_two_outside_river = not self.xiang_gain_jump_two_outside_river
            elif self.ma_straight_checkbox.collidepoint(mouse_pos):
                self.ma_can_straight_three = not self.ma_can_straight_three
            # 检查按钮点击
            elif self.confirm_button.is_clicked(mouse_pos, event):
                return "confirm"
            elif self.back_button.is_clicked(mouse_pos, event):
                return "back"
        
        # 更新按钮悬停状态
        self.confirm_button.check_hover(mouse_pos)
        self.back_button.check_hover(mouse_pos)
        
        return None
    
    def get_settings(self):
        """获取当前设置"""
        settings = {
            "king_can_leave_palace": self.king_can_leave_palace,
            "king_lose_diagonal_outside_palace": self.king_lose_diagonal_outside_palace,
            "king_can_diagonal_in_palace": self.king_can_diagonal_in_palace,
            "shi_can_leave_palace": self.shi_can_leave_palace,
            "shi_gain_straight_outside_palace": self.shi_gain_straight_outside_palace,
            "xiang_can_cross_river": self.xiang_can_cross_river,
            "xiang_gain_jump_two_outside_river": self.xiang_gain_jump_two_outside_river,
            "ma_can_straight_three": self.ma_can_straight_three
        }
        
        # 保存设置到全局配置
        game_config.update_settings(settings)
        
        return settings
    
    def run(self):
        """运行设置界面"""
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
                    self.window_width, self.window_height = event.w, event.h
                    self.screen = pygame.display.set_mode((self.window_width, self.window_height), pygame.RESIZABLE)
                    self.create_ui_elements()
                
                # 处理键盘事件
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        return "back"
                
                # 处理鼠标事件
                result = self.handle_event(event, mouse_pos)
                if result == "confirm":
                    return self.get_settings()
                elif result == "back":
                    return "back"
            
            # 绘制界面
            self.draw()
            pygame.display.flip()
            clock.tick(60)
        
        return "back"