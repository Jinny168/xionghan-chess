import pygame

from program.config.config import BLACK, RED, POPUP_BG
from program.ui.button import Button
from program.utils.utils import load_font

class AudioSettingsDialog:
    """音效设置对话框"""
    def __init__(self, width, height, sound_manager):
        self.width = 600  # 增加对话框宽度以更好地容纳所有元素
        self.height = 400  # 进一步增加对话框高度以适应新添加的音乐风格切换选项
        self.sound_manager = sound_manager  # 音效管理器引用
        self.x = 0
        self.y = 0
        
        # 音量值 (0.0 - 1.0)
        self.music_volume = sound_manager.music_volume
        self.sound_volume = sound_manager.sound_volume
        
        # 音乐风格
        self.current_music_style = sound_manager.current_music_style
        
        # 按钮尺寸
        self.button_width = 120
        self.button_height = 40
        self.button_spacing = 20
        
        # 创建按钮
        self.ok_button = Button(0, 0, self.button_width, self.button_height, "确定")
        self.cancel_button = Button(0, 0, self.button_width, self.button_height, "取消")
        self.reset_button = Button(0, 0, self.button_width, self.button_height, "重置")
        
        # 预创建覆盖层表面
        self.overlay_surface = None

    def draw(self, screen):
        # 获取当前窗口尺寸
        window_width, window_height = screen.get_size()
        
        # 重新计算弹窗位置
        self.x = (window_width - self.width) // 2
        self.y = (window_height - self.height) // 2
        
        # 更新按钮位置
        # 三个按钮水平排列，平均分布在对话框底部
        total_buttons_width = 3 * self.button_width + 2 * self.button_spacing
        buttons_start_x = self.x + (self.width - total_buttons_width) // 2
        button_y = self.y + self.height - self.button_height - 20
        
        self.ok_button.update_position(buttons_start_x, button_y)
        self.reset_button.update_position(buttons_start_x + self.button_width + self.button_spacing, button_y)
        self.cancel_button.update_position(buttons_start_x + 2 * (self.button_width + self.button_spacing), button_y)
        
        # 绘制半透明背景
        if self.overlay_surface is None or self.overlay_surface.get_size() != (window_width, window_height):
            self.overlay_surface = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        self.overlay_surface.fill((0, 0, 0, 128))  # 半透明黑色
        screen.blit(self.overlay_surface, (0, 0))
        
        # 绘制弹窗主体
        pygame.draw.rect(screen, POPUP_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 3)
        
        # 添加装饰边框
        inner_margin = 10
        pygame.draw.rect(
            screen, 
            (180, 180, 180), 
            (self.x + inner_margin, self.y + inner_margin, 
             self.width - 2*inner_margin, self.height - 2*inner_margin), 
            2
        )
        
        # 绘制标题文本
        font_big = load_font(36)
        text_surface = font_big.render("音效设置", True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 40))
        screen.blit(text_surface, text_rect)
        
        # 绘制音量调节说明
        font_medium = load_font(24)
        small_font = load_font(18)
        
        # 背景音乐音量
        music_label = font_medium.render("背景音乐音量:", True, BLACK)
        screen.blit(music_label, (self.x + 50, self.y + 100))
        # 音效音量
        sound_label = font_medium.render("音效音量:", True, BLACK)
        screen.blit(sound_label, (self.x + 50, self.y + 180))
        
        # 音乐风格切换
        style_label = font_medium.render("FC/QQ音乐风格切换:", True, BLACK)
        screen.blit(style_label, (self.x + 50, self.y + 260))
        
        # 音量条背景
        bar_width = 250  # 增加音量条长度以利用额外的宽度
        bar_height = 20
        bar_x = self.x + 200  # 调整位置以适应更长的音量条
        # 音乐音量条
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, self.y + 105, bar_width, bar_height))
        pygame.draw.rect(screen, (100, 150, 255), (bar_x, self.y + 105, int(bar_width * self.music_volume), bar_height))
        pygame.draw.rect(screen, BLACK, (bar_x, self.y + 105, bar_width, bar_height), 2)
        # 显示具体数值
        vol_text = small_font.render(f"{self.music_volume:.2f}", True, BLACK)
        screen.blit(vol_text, (bar_x + bar_width + 10, self.y + 105))
        # 音乐音量条标签
        vol_small_text = small_font.render("← 小", True, BLACK)
        screen.blit(vol_small_text, (bar_x - 40, self.y + 130))
        vol_large_text = small_font.render("大 →", True, BLACK)
        screen.blit(vol_large_text, (bar_x + bar_width + 10, self.y + 130))
        
        # 音效音量条
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, self.y + 185, bar_width, bar_height))
        pygame.draw.rect(screen, (255, 150, 100), (bar_x, self.y + 185, int(bar_width * self.sound_volume), bar_height))
        pygame.draw.rect(screen, BLACK, (bar_x, self.y + 185, bar_width, bar_height), 2)
        # 显示具体数值
        vol_text = small_font.render(f"{self.sound_volume:.2f}", True, BLACK)
        screen.blit(vol_text, (bar_x + bar_width + 10, self.y + 185))
        # 音效音量条标签
        vol_small_text = small_font.render("← 小", True, BLACK)
        screen.blit(vol_small_text, (bar_x - 40, self.y + 210))
        vol_large_text = small_font.render("大 →", True, BLACK)
        screen.blit(vol_large_text, (bar_x + bar_width + 10, self.y + 210))
        
        # 绘制音乐风格切换复选框
        checkbox_size = 20
        checkbox_x = bar_x  # 与音量条对齐
        checkbox_y = self.y + 265  # 与文字对齐
        pygame.draw.rect(screen, BLACK, (checkbox_x, checkbox_y, checkbox_size, checkbox_size), 2)
        if self.current_music_style == 'fc':
            # 如果是FC风格，画一个勾
            pygame.draw.line(screen, BLACK, (checkbox_x + 4, checkbox_y + 10), 
                             (checkbox_x + 8, checkbox_y + 15), 2)
            pygame.draw.line(screen, BLACK, (checkbox_x + 8, checkbox_y + 15), 
                             (checkbox_x + 16, checkbox_y + 5), 2)
        # 显示当前风格
        style_text = small_font.render(f"当前: {'FC风格' if self.current_music_style == 'fc' else 'QQ风格'}", True, BLACK)
        screen.blit(style_text, (checkbox_x + checkbox_size + 10, checkbox_y))
        
        # 绘制按钮
        self.ok_button.draw(screen)
        self.reset_button.draw(screen)
        self.cancel_button.draw(screen)

    def handle_event(self, event, mouse_pos):
        # 如果按钮尚未创建，返回None
        if not self.ok_button or not self.cancel_button or not self.reset_button:
            return None

        # 处理鼠标悬停
        self.ok_button.check_hover(mouse_pos)
        self.reset_button.check_hover(mouse_pos)
        self.cancel_button.check_hover(mouse_pos)
        
        # 检查按钮点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查按钮点击，优先级高于音量条
            if self.ok_button.is_clicked(mouse_pos, event):
                # 应用设置并关闭对话框
                self.sound_manager.set_music_volume(self.music_volume)
                self.sound_manager.set_sound_volume(self.sound_volume)
                # 切换音乐风格
                if self.current_music_style != self.sound_manager.current_music_style:
                    self.sound_manager.toggle_music_style()
                return "ok"  # 确认
            elif self.cancel_button.is_clicked(mouse_pos, event):
                return "cancel"  # 取消，不保存更改
            elif self.reset_button.is_clicked(mouse_pos, event):
                # 重置为默认值
                self.music_volume = 0.5
                self.sound_volume = 0.7
                self.current_music_style = 'fc'  # 重置为默认风格
                self.sound_manager.set_music_volume(self.music_volume)
                self.sound_manager.set_sound_volume(self.sound_volume)
                return "reset"  # 重置
            
            # 检查音乐风格切换复选框点击
            checkbox_size = 20
            checkbox_x = self.x + 200  # 与音量条对齐
            checkbox_y = self.y + 265
            checkbox_rect = pygame.Rect(checkbox_x, checkbox_y, checkbox_size, checkbox_size)
            if checkbox_rect.collidepoint(mouse_pos):
                # 切换音乐风格
                self.current_music_style = 'qq' if self.current_music_style == 'fc' else 'fc'
                # 立即应用音乐风格切换
                if self.current_music_style != self.sound_manager.current_music_style:
                    self.sound_manager.toggle_music_style()
                return "style_changed"

        # 检查是否是鼠标按下事件或鼠标移动事件（在鼠标按键状态下）来处理音量条
        if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]):
            bar_width = 250  # 与绘制时的长度一致
            bar_x = self.x + 200  # 与绘制时的位置一致

            # 检查是否点击/拖动音乐音量条
            music_bar_y = self.y + 105
            # 检查是否在音量条的Y范围内，允许一定的容错
            if (music_bar_y - 10 <= mouse_pos[1] <= music_bar_y + 20 + 10):
                # 检查是否在音量条的X范围内或鼠标按键被按下（允许拖动超出边界）
                if (bar_x - 10 <= mouse_pos[0] <= bar_x + bar_width + 10) or pygame.mouse.get_pressed()[0]:
                    # 计算音量，限制在条形范围内
                    raw_volume = (mouse_pos[0] - bar_x) / bar_width
                    self.music_volume = max(0.0, min(1.0, raw_volume))
                    self.sound_manager.set_music_volume(self.music_volume)
                    return "volume_changed"

            # 检查是否点击/拖动音效音量条
            sound_bar_y = self.y + 185
            # 检查是否在音量条的Y范围内，允许一定的容错
            if (sound_bar_y - 10 <= mouse_pos[1] <= sound_bar_y + 20 + 10):
                # 检查是否在音量条的X范围内或鼠标按键被按下（允许拖动超出边界）
                if (bar_x - 10 <= mouse_pos[0] <= bar_x + bar_width + 10) or pygame.mouse.get_pressed()[0]:
                    # 计算音量，限制在条形范围内
                    raw_volume = (mouse_pos[0] - bar_x) / bar_width
                    self.sound_volume = max(0.0, min(1.0, raw_volume))
                    self.sound_manager.set_sound_volume(self.sound_volume)
                    return "volume_changed"

        return None  # 对话框保持打开状态

class PopupDialog:
    def __init__(self, width, height, message, total_time=0, red_time=0, black_time=0):
        self.width = width
        self.height = height
        self.message = message
        self.total_time = total_time
        self.red_time = red_time
        self.black_time = black_time
        
        # 计算弹窗位置 - 会在绘制时动态计算
        self.x = 0
        self.y = 0
        
        # 创建按钮
        button_width = 120
        button_height = 40
        self.button_width = button_width
        self.button_height = button_height
        
        # 创建多个按钮
        self.restart_button = Button(0, 0, button_width, button_height, "重新开始")
        self.replay_button = Button(0, 0, button_width, button_height, "复盘")
        
        # 预创建覆盖层表面
        self.overlay_surface = None
        
    def draw(self, screen):
        # 获取当前窗口尺寸
        window_width, window_height = screen.get_size()
        
        # 重新计算弹窗位置
        self.x = (window_width - self.width) // 2
        self.y = (window_height - self.height) // 2
        
        # 计算按钮位置（两个按钮水平排列）
        total_button_width = 2 * self.button_width + 20  # 20是按钮间的间距
        start_x = self.x + (self.width - total_button_width) // 2
        button_y = self.y + self.height - self.button_height - 20
        
        self.restart_button.update_position(start_x, button_y)
        self.replay_button.update_position(start_x + self.button_width + 20, button_y)
        
        # 绘制半透明背景
        if self.overlay_surface is None or self.overlay_surface.get_size() != (window_width, window_height):
            self.overlay_surface = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        self.overlay_surface.fill((0, 0, 0, 128))  # 半透明黑色
        screen.blit(self.overlay_surface, (0, 0))
        
        # 绘制弹窗主体
        pygame.draw.rect(screen, POPUP_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 3)
        
        # 添加装饰边框
        inner_margin = 10
        pygame.draw.rect(
            screen, 
            (180, 180, 180), 
            (self.x + inner_margin, self.y + inner_margin, 
             self.width - 2*inner_margin, self.height - 2*inner_margin), 
            2
        )
        
        # 绘制标题文本
        font_big = load_font(40)
        text_surface = font_big.render("游戏结束", True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 50))
        screen.blit(text_surface, text_rect)
        
        # 绘制结果文本
        font = load_font(32)
        text_surface = font.render(self.message, True, RED if "胜利" in self.message else (0, 0, 0))
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 110))
        screen.blit(text_surface, text_rect)
        
        # 如果是和棋，显示和棋原因
        if "平局" in self.message or "和" in self.message:
            # 尝试获取和棋原因（如果game_state可用）
            try:
                # 这里需要在调用处传递game_state或和棋原因
                pass
            except:
                pass
        
        # 绘制时间信息
        time_font = load_font(20)
        
        # 显示总用时
        total_time_str = f"{int(self.total_time//60):02}:{int(self.total_time%60):02}"
        total_time_text = f"对局总时长: {total_time_str}"
        total_time_surface = time_font.render(total_time_text, True, BLACK)
        total_time_rect = total_time_surface.get_rect(center=(window_width//2, self.y + 160))
        screen.blit(total_time_surface, total_time_rect)
        
        # 显示红方用时
        red_time_str = f"{int(self.red_time//60):02}:{int(self.red_time%60):02}"
        red_time_text = f"红方用时: {red_time_str}"
        red_time_surface = time_font.render(red_time_text, True, RED)
        red_time_rect = red_time_surface.get_rect(center=(window_width//2, self.y + 190))
        screen.blit(red_time_surface, red_time_rect)
        
        # 显示黑方用时
        black_time_str = f"{int(self.black_time//60):02}:{int(self.black_time%60):02}"
        black_time_text = f"黑方用时: {black_time_str}"
        black_time_surface = time_font.render(black_time_text, True, BLACK)
        black_time_rect = black_time_surface.get_rect(center=(window_width//2, self.y + 220))
        screen.blit(black_time_surface, black_time_rect)
        
        # 如果是和棋，添加和棋说明
        if "平局" in self.message:
            draw_y = 250
            draw_explanation = time_font.render("和棋原因: 双方均无可能取胜的简单局势", True, (0, 0, 0))
            screen.blit(draw_explanation, (window_width//2 - draw_explanation.get_width()//2, self.y + draw_y))
        
        # 绘制按钮
        self.restart_button.draw(screen)
        self.replay_button.draw(screen)
    
    def handle_event(self, event, mouse_pos):
        # 如果按钮尚未创建，返回False
        if not self.restart_button or not self.replay_button:
            return False
            
        # 处理鼠标悬停
        self.restart_button.check_hover(mouse_pos)
        self.replay_button.check_hover(mouse_pos)
        
        # 检查按钮点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.restart_button.is_clicked(mouse_pos, event):
                return "restart"
            elif self.replay_button.is_clicked(mouse_pos, event):
                return "replay"
        return False

class ConfirmDialog:
    def __init__(self, width, height, message):
        self.width = width
        self.height = height
        self.message = message
        
        # 计算弹窗位置 - 会在绘制时动态计算
        self.x = 0
        self.y = 0
        
        # 按钮尺寸
        self.button_width = 120
        self.button_height = 40
        self.button_spacing = 30
        
        # 预先创建按钮，避免重复创建
        self.confirm_button = Button(0, 0, self.button_width, self.button_height, "确认")
        self.cancel_button = Button(0, 0, self.button_width, self.button_height, "取消")
        
        # 结果
        self.result = None  # None = 未选择, True = 确认, False = 取消
        
        # 预创建覆盖层表面
        self.overlay_surface = None
        
    def draw(self, screen):
        # 获取当前窗口尺寸
        window_width, window_height = screen.get_size()
        
        # 重新计算弹窗位置
        self.x = (window_width - self.width) // 2
        self.y = (window_height - self.height) // 2
        
        # 更新按钮位置
        confirm_x = self.x + (self.width // 2) - self.button_width - (self.button_spacing // 2)
        confirm_y = self.y + self.height - self.button_height - 20
        self.confirm_button.update_position(confirm_x, confirm_y)
        
        cancel_x = self.x + (self.width // 2) + (self.button_spacing // 2)
        cancel_y = self.y + self.height - self.button_height - 20
        self.cancel_button.update_position(cancel_x, cancel_y)
        
        # 绘制半透明背景
        if self.overlay_surface is None or self.overlay_surface.get_size() != (window_width, window_height):
            self.overlay_surface = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        self.overlay_surface.fill((0, 0, 0, 128))  # 半透明黑色
        screen.blit(self.overlay_surface, (0, 0))
        
        # 绘制弹窗主体
        pygame.draw.rect(screen, POPUP_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 3)
        
        # 添加装饰边框
        inner_margin = 10
        pygame.draw.rect(
            screen, 
            (180, 180, 180), 
            (self.x + inner_margin, self.y + inner_margin, 
             self.width - 2*inner_margin, self.height - 2*inner_margin), 
            2
        )
        
        # 绘制标题文本
        font_big = load_font(36)
        text_surface = font_big.render("确认", True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 40))
        screen.blit(text_surface, text_rect)
        
        # 绘制确认信息文本
        font = load_font(24)
        # 处理消息换行显示
        lines = self.message.split('\n')
        line_height = 30
        start_y = self.y + 90
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, BLACK)
            text_rect = text_surface.get_rect(center=(window_width//2, start_y + i * line_height))
            screen.blit(text_surface, text_rect)
        
        # 绘制按钮
        self.confirm_button.draw(screen)
        self.cancel_button.draw(screen)
    
    def handle_event(self, event, mouse_pos):
        # 如果按钮尚未创建，返回None
        if not self.confirm_button or not self.cancel_button:
            return None
            
        # 处理鼠标悬停
        self.confirm_button.check_hover(mouse_pos)
        self.cancel_button.check_hover(mouse_pos)
        
        # 检查按钮点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.confirm_button.rect.collidepoint(mouse_pos):
                self.result = True
                return self.result
            elif self.cancel_button.rect.collidepoint(mouse_pos):
                self.result = False
                return self.result
        
        return self.result

class PawnResurrectionDialog:
    """兵/卒复活确认对话框"""
    def __init__(self, width, height, player_color, position):
        self.width = width
        self.height = height
        self.player_color = player_color
        self.position = position  # (row, col)
        
        # 计算弹窗位置
        self.x = 0
        self.y = 0
        
        # 按钮尺寸
        self.button_width = 120
        self.button_height = 40
        self.button_spacing = 30
        
        # 预先创建按钮
        self.confirm_button = Button(0, 0, self.button_width, self.button_height, "确认")
        self.cancel_button = Button(0, 0, self.button_width, self.button_height, "取消")
        
        # 结果
        self.result = None  # None = 未选择, True = 确认, False = 取消
        
        # 预创建覆盖层表面
        self.overlay_surface = None
    
    def draw(self, screen):
        # 获取当前窗口尺寸
        window_width, window_height = screen.get_size()
        
        # 重新计算弹窗位置
        self.x = (window_width - self.width) // 2
        self.y = (window_height - self.height) // 2
        
        # 更新按钮位置
        confirm_x = self.x + (self.width // 2) - self.button_width - (self.button_spacing // 2)
        confirm_y = self.y + self.height - self.button_height - 20
        self.confirm_button.update_position(confirm_x, confirm_y)
        
        cancel_x = self.x + (self.width // 2) + (self.button_spacing // 2)
        cancel_y = self.y + self.height - self.button_height - 20
        self.cancel_button.update_position(cancel_x, cancel_y)
        
        # 绘制半透明背景
        if self.overlay_surface is None or self.overlay_surface.get_size() != (window_width, window_height):
            self.overlay_surface = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        self.overlay_surface.fill((0, 0, 0, 128))  # 半透明黑色
        screen.blit(self.overlay_surface, (0, 0))
        
        # 绘制弹窗主体
        pygame.draw.rect(screen, POPUP_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 3)
        
        # 添加装饰边框
        inner_margin = 10
        pygame.draw.rect(
            screen, 
            (180, 180, 180), 
            (self.x + inner_margin, self.y + inner_margin, 
             self.width - 2*inner_margin, self.height - 2*inner_margin), 
            2
        )
        
        # 绘制标题文本
        font_big = load_font(36)
        text_surface = font_big.render("兵卒复活确认", True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 40))
        screen.blit(text_surface, text_rect)
        
        # 绘制确认信息文本
        font = load_font(24)
        message = "是否消耗本次走子机会，在当前位置复活1个兵/卒？"
        
        # 处理消息换行显示
        lines = [message[i:i+30] for i in range(0, len(message), 30)]  # 每行最多30个字符
        line_height = 30
        start_y = self.y + 90
        
        for i, line in enumerate(lines):
            text_surface = font.render(line, True, BLACK)
            text_rect = text_surface.get_rect(center=(window_width//2, start_y + i * line_height))
            screen.blit(text_surface, text_rect)
        
        # 绘制按钮
        self.confirm_button.draw(screen)
        self.cancel_button.draw(screen)
    
    def handle_event(self, event, mouse_pos):
        # 如果按钮尚未创建，返回None
        if not self.confirm_button or not self.cancel_button:
            return None
            
        # 处理鼠标悬停
        self.confirm_button.check_hover(mouse_pos)
        self.cancel_button.check_hover(mouse_pos)
        
        # 检查按钮点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            if self.confirm_button.rect.collidepoint(mouse_pos):
                self.result = True
                return self.result
            elif self.cancel_button.rect.collidepoint(mouse_pos):
                self.result = False
                return self.result
        
        return self.result

class PromotionDialog:
    """兵卒冲底升变选择对话框"""
    def __init__(self, width, height, player_color, position, captured_pieces):
        self.width = width
        self.height = height
        self.player_color = player_color
        self.position = position  # (row, col)
        self.captured_pieces = captured_pieces  # 阵亡棋子列表
        self.selected_piece_index = None  # 选中的阵亡棋子索引
        
        # 计算弹窗位置
        self.x = 0
        self.y = 0
        
        # 按钮尺寸
        self.button_width = 120
        self.button_height = 40
        self.button_spacing = 30
        
        # 预先创建按钮
        self.promote_button = Button(0, 0, self.button_width, self.button_height, "升变")
        self.cancel_button = Button(0, 0, self.button_width, self.button_height, "取消")
        
        # 结果
        self.result = None  # None = 未选择, (True, index) = 确认并选择的索引, False = 取消
        self.selected_index = None  # 选中的棋子索引
        
        # 预创建覆盖层表面
        self.overlay_surface = None
        
        # 列表滚动
        self.scroll_offset = 0
        self.max_visible_items = 8  # 最多显示8个棋子
    
    def draw(self, screen):
        # 获取当前窗口尺寸
        window_width, window_height = screen.get_size()
        
        # 重新计算弹窗位置
        self.x = (window_width - self.width) // 2
        self.y = (window_height - self.height) // 2
        
        # 更新按钮位置
        promote_x = self.x + (self.width // 2) - self.button_width - (self.button_spacing // 2)
        promote_y = self.y + self.height - self.button_height - 20
        self.promote_button.update_position(promote_x, promote_y)
        
        cancel_x = self.x + (self.width // 2) + (self.button_spacing // 2)
        cancel_y = self.y + self.height - self.button_height - 20
        self.cancel_button.update_position(cancel_x, cancel_y)
        
        # 绘制半透明背景
        if self.overlay_surface is None or self.overlay_surface.get_size() != (window_width, window_height):
            self.overlay_surface = pygame.Surface((window_width, window_height), pygame.SRCALPHA)
        self.overlay_surface.fill((0, 0, 0, 128))  # 半透明黑色
        screen.blit(self.overlay_surface, (0, 0))
        
        # 绘制弹窗主体
        pygame.draw.rect(screen, POPUP_BG, (self.x, self.y, self.width, self.height))
        pygame.draw.rect(screen, BLACK, (self.x, self.y, self.width, self.height), 3)
        
        # 添加装饰边框
        inner_margin = 10
        pygame.draw.rect(
            screen, 
            (180, 180, 180), 
            (self.x + inner_margin, self.y + inner_margin, 
             self.width - 2*inner_margin, self.height - 2*inner_margin), 
            2
        )
        
        # 绘制标题文本
        font_big = load_font(36)
        text_surface = font_big.render("升变选择", True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 40))
        screen.blit(text_surface, text_rect)
        
        # 绘制提示信息文本
        font = load_font(20)
        message = "兵卒已冲底！请从以下阵亡棋子中选择1个进行升变："
        text_surface = font.render(message, True, BLACK)
        text_rect = text_surface.get_rect(center=(window_width//2, self.y + 80))
        screen.blit(text_surface, text_rect)
        
        # 绘制阵亡棋子列表
        list_start_y = self.y + 120
        item_height = 30
        visible_items = min(self.max_visible_items, len(self.captured_pieces))
        list_height = visible_items * item_height + 10  # 10为边距
        list_width = self.width - 40  # 20为左右边距
        list_x = self.x + 20
        list_y = list_start_y
        
        # 绘制列表边框
        pygame.draw.rect(screen, BLACK, (list_x, list_y, list_width, list_height), 2)
        
        # 绘制列表内容
        for i in range(visible_items):
            idx = i + self.scroll_offset
            if idx >= len(self.captured_pieces):
                break
                
            piece = self.captured_pieces[idx]
            item_y = list_y + 5 + i * item_height  # 5为顶部边距
            
            # 如果是选中的项目，绘制背景
            if self.selected_piece_index == idx:
                pygame.draw.rect(screen, (180, 180, 255), (list_x + 2, item_y, list_width - 4, item_height - 2))
            
            # 绘制棋子名称
            piece_text = font.render(f"{piece.name}({piece.__class__.__name__})", True, BLACK)
            screen.blit(piece_text, (list_x + 10, item_y + 5))
        
        # 绘制滚动提示（如果有更多项目）
        if len(self.captured_pieces) > self.max_visible_items:
            scroll_text = load_font(16).render(f"↑↓ 滚动 (共{len(self.captured_pieces)}项)", True, BLACK)
            screen.blit(scroll_text, (list_x, list_y + list_height + 5))
        
        # 绘制按钮
        self.promote_button.draw(screen)
        self.cancel_button.draw(screen)
    
    def handle_event(self, event, mouse_pos):
        # 如果按钮尚未创建，返回None
        if not self.promote_button or not self.cancel_button:
            return None
            
        # 处理鼠标悬停
        self.promote_button.check_hover(mouse_pos)
        self.cancel_button.check_hover(mouse_pos)
        
        # 检查按钮点击
        if event.type == pygame.MOUSEBUTTONDOWN:
            # 检查是否点击了列表区域
            list_start_y = self.y + 120
            list_height = min(self.max_visible_items, len(self.captured_pieces)) * 30 + 10
            list_x = self.x + 20
            list_y = list_start_y
            
            if (list_x <= mouse_pos[0] <= list_x + (self.width - 40) and
                list_y <= mouse_pos[1] <= list_y + list_height and
                len(self.captured_pieces) > 0):
                
                # 计算点击的项目索引
                relative_y = mouse_pos[1] - list_y - 5  # 减去顶部边距
                clicked_index = relative_y // 30 + self.scroll_offset
                
                if clicked_index < len(self.captured_pieces):
                    self.selected_piece_index = clicked_index
                    return None  # 仅选择，不返回结果
            
            # 检查按钮点击
            if self.promote_button.rect.collidepoint(mouse_pos) and self.selected_piece_index is not None:
                self.result = (True, self.selected_piece_index)
                return self.result
            elif self.cancel_button.rect.collidepoint(mouse_pos):
                self.result = False
                return self.result
        
        # 处理鼠标滚轮滚动列表
        if event.type == pygame.MOUSEWHEEL:
            list_start_y = self.y + 120
            list_height = min(self.max_visible_items, len(self.captured_pieces)) * 30 + 10
            list_x = self.x + 20
            list_y = list_start_y
            
            if (list_x <= mouse_pos[0] <= list_x + (self.width - 40) and
                list_y <= mouse_pos[1] <= list_y + list_height):
                
                if event.y > 0:  # 向上滚动
                    self.scroll_offset = max(0, self.scroll_offset - 1)
                elif event.y < 0:  # 向下滚动
                    max_scroll = max(0, len(self.captured_pieces) - self.max_visible_items)
                    self.scroll_offset = min(max_scroll, self.scroll_offset + 1)
        
        return self.result
