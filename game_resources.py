"""游戏资源管理模块，包含音效、资源路径等"""
import os
import sys
import pygame


def resource_path(relative_path):
    """获取资源文件的绝对路径，兼容PyInstaller打包后的环境"""
    try:
        # PyInstaller创建的临时文件夹存储在sys._MEIPASS中
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)


class SoundManager:
    """音效管理器"""
    def __init__(self):
        self.check_sound = None
        self.move_sound = None
        self.capture_sound = None
        self.load_sounds()

    def load_sounds(self):
        """加载音效"""
        try:
            # 使用完整路径加载音效
            check_sound_path = resource_path(os.path.join("sounds", "check.wav"))
            move_sound_path = resource_path(os.path.join("sounds", "move.wav"))
            capture_sound_path = resource_path(os.path.join("sounds", "capture.wav"))

            self.check_sound = pygame.mixer.Sound(check_sound_path)
            self.move_sound = pygame.mixer.Sound(move_sound_path)
            self.capture_sound = pygame.mixer.Sound(capture_sound_path)

            # 设置音量（值范围0.0到1.0）
            self.check_sound.set_volume(0.8)  # 将军音效音量设为80%
            self.move_sound.set_volume(0.6)  # 移动音效音量设为60%
            self.capture_sound.set_volume(0.7)  # 吃子音效音量设为70%
        except Exception as e:
            # 如果找不到音效文件，创建空声音对象
            self.check_sound = pygame.mixer.Sound(bytes(bytearray(100)))
            self.move_sound = pygame.mixer.Sound(bytes(bytearray(100)))
            self.capture_sound = pygame.mixer.Sound(bytes(bytearray(100)))
            # 设置音量为0（无声）
            self.check_sound.set_volume(0)
            self.move_sound.set_volume(0)
            self.capture_sound.set_volume(0)
            print(f"警告：未能加载音效文件。错误: {e}")

    def play_check_sound(self):
        """播放将军音效"""
        if self.check_sound:
            try:
                self.check_sound.play()
            except:
                pass

    def play_move_sound(self):
        """播放移动音效"""
        if self.move_sound:
            try:
                self.move_sound.play()
            except:
                pass

    def play_capture_sound(self):
        """播放吃子音效"""
        if self.capture_sound:
            try:
                self.capture_sound.play()
            except:
                pass


class GameTimer:
    """游戏计时器管理"""
    def __init__(self):
        self.clock = None
        self.init_clock()

    def init_clock(self):
        """初始化时钟"""
        self.clock = pygame.time.Clock()

    def tick(self, fps):
        """控制帧率"""
        if self.clock:
            self.clock.tick(fps)