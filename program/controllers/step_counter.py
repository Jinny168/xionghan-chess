class StepCounter:
    """步数计数器类，用于跟踪游戏步数"""

    def __init__(self):
        self.step_count = 0

    def increment(self):
        """增加步数"""
        self.step_count += 1
        return self.step_count

    def reset(self):
        """重置步数"""
        self.step_count = 0

    def get_step(self):
        """获取当前步数"""
        return self.step_count


# 全局步数计数器实例
step_counter = StepCounter()