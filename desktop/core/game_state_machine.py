"""
游戏状态机 - 管理游戏生命周期状态转换
"""
from enum import Enum, auto
from typing import Optional, Callable, Dict
from desktop.utils.logger import get_module_logger

logger = get_module_logger("state_machine")


class GamePhase(Enum):
    """游戏阶段枚举"""
    INITIALIZING = auto()      # 初始化中
    MENU = auto()              # 主菜单
    MODE_SELECTION = auto()    # 模式选择
    CAMP_SELECTION = auto()    # 阵营选择
    GAME_RUNNING = auto()      # 游戏进行中
    PAUSED = auto()            # 暂停
    THINKING = auto()          # AI思考中
    PROMOTION = auto()         # 升变选择
    RESURRECTION = auto()      # 复活选择
    GAME_OVER = auto()         # 游戏结束
    REPLAY_MODE = auto()       # 复盘模式
    SETTINGS = auto()          # 设置界面
    NETWORK_CONNECTING = auto() # 网络连接中
    QUITTING = auto()          # 退出中


class StateTransition:
    """状态转换规则"""
    
    def __init__(
        self,
        from_state: GamePhase,
        to_state: GamePhase,
        condition: Optional[Callable] = None,
        on_enter: Optional[Callable] = None,
        on_exit: Optional[Callable] = None
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.condition = condition  # 转换条件
        self.on_enter = on_enter    # 进入新状态时的回调
        self.on_exit = on_exit      # 离开旧状态时的回调
    
    def can_transition(self) -> bool:
        """检查是否可以进行状态转换"""
        if self.condition:
            return self.condition()
        return True
    
    def execute_transition(self):
        """执行状态转换"""
        if self.on_exit:
            self.on_exit()
        if self.on_enter:
            self.on_enter()


class GameStateMachine:
    """
    游戏状态机
    管理游戏状态的转换和生命周期
    """
    
    def __init__(self):
        self.current_state: GamePhase = GamePhase.INITIALIZING
        self.previous_state: Optional[GamePhase] = None
        
        # 状态转换规则
        self.transitions: Dict[tuple, StateTransition] = {}
        
        # 状态处理器映射
        self.state_handlers: Dict[GamePhase, Callable] = {}
        
        # 注册默认转换规则
        self._register_default_transitions()
        
        logger.info(f"GameStateMachine initialized, current state: {self.current_state}")
    
    def _register_default_transitions(self):
        """注册默认的状态转换规则"""
        
        # 初始化 -> 菜单
        self.add_transition(
            GamePhase.INITIALIZING,
            GamePhase.MENU,
            on_enter=lambda: logger.info("进入游戏菜单")
        )
        
        # 菜单 -> 模式选择
        self.add_transition(
            GamePhase.MENU,
            GamePhase.MODE_SELECTION,
            on_enter=lambda: logger.info("进入模式选择")
        )
        
        # 模式选择 -> 阵营选择（PVC模式）
        self.add_transition(
            GamePhase.MODE_SELECTION,
            GamePhase.CAMP_SELECTION,
            condition=lambda: True,  # 需要根据实际模式判断
            on_enter=lambda: logger.info("进入阵营选择")
        )
        
        # 阵营选择 -> 游戏运行
        self.add_transition(
            GamePhase.CAMP_SELECTION,
            GamePhase.GAME_RUNNING,
            on_enter=lambda: logger.info("游戏开始")
        )
        
        # 模式选择 -> 游戏运行（PVP）
        self.add_transition(
            GamePhase.MODE_SELECTION,
            GamePhase.GAME_RUNNING,
            on_enter=lambda: logger.info("游戏开始（PVP）")
        )
        
        # 菜单 -> 游戏运行（快速开始）
        self.add_transition(
            GamePhase.MENU,
            GamePhase.GAME_RUNNING,
            on_enter=lambda: logger.info("游戏开始")
        )
        
        # 游戏运行 -> 暂停
        self.add_transition(
            GamePhase.GAME_RUNNING,
            GamePhase.PAUSED,
            on_enter=lambda: logger.info("游戏暂停")
        )
        
        # 暂停 -> 游戏运行
        self.add_transition(
            GamePhase.PAUSED,
            GamePhase.GAME_RUNNING,
            on_enter=lambda: logger.info("游戏恢复")
        )
        
        # 游戏运行 -> AI思考
        self.add_transition(
            GamePhase.GAME_RUNNING,
            GamePhase.THINKING,
            on_enter=lambda: logger.debug("AI开始思考")
        )
        
        # AI思考 -> 游戏运行
        self.add_transition(
            GamePhase.THINKING,
            GamePhase.GAME_RUNNING,
            on_enter=lambda: logger.debug("AI思考完成")
        )
        
        # 游戏运行 -> 升变
        self.add_transition(
            GamePhase.GAME_RUNNING,
            GamePhase.PROMOTION,
            on_enter=lambda: logger.info("进入升变选择")
        )
        
        # 升变 -> 游戏运行
        self.add_transition(
            GamePhase.PROMOTION,
            GamePhase.GAME_RUNNING,
            on_enter=lambda: logger.info("升变完成")
        )
        
        # 游戏运行 -> 游戏结束
        self.add_transition(
            GamePhase.GAME_RUNNING,
            GamePhase.GAME_OVER,
            on_enter=lambda: logger.info("游戏结束")
        )
        
        # 游戏结束 -> 菜单
        self.add_transition(
            GamePhase.GAME_OVER,
            GamePhase.MENU,
            on_enter=lambda: logger.info("返回主菜单")
        )
        
        # 任意状态 -> 设置
        self.add_transition(
            None,  # None表示从任意状态
            GamePhase.SETTINGS,
            on_enter=lambda: logger.info("进入设置界面")
        )
        
        # 设置 -> 之前的状态
        self.add_transition(
            GamePhase.SETTINGS,
            None,  # 返回之前的状态
            on_exit=lambda: logger.info("退出设置界面")
        )
        
        # 任意状态 -> 退出
        self.add_transition(
            None,
            GamePhase.QUITTING,
            on_enter=lambda: logger.info("准备退出游戏")
        )
    
    def add_transition(
        self,
        from_state: Optional[GamePhase],
        to_state: Optional[GamePhase],
        condition: Optional[Callable] = None,
        on_enter: Optional[Callable] = None,
        on_exit: Optional[Callable] = None
    ):
        """
        添加状态转换规则
        
        Args:
            from_state: 源状态（None表示任意状态）
            to_state: 目标状态
            condition: 转换条件函数
            on_enter: 进入新状态的回调
            on_exit: 离开旧状态的回调
        """
        key = (from_state, to_state)
        transition = StateTransition(
            from_state or GamePhase.INITIALIZING,
            to_state or self.current_state,
            condition,
            on_enter,
            on_exit
        )
        self.transitions[key] = transition
    
    def transition_to(self, new_state: GamePhase, **kwargs) -> bool:
        """
        转换到新状态
        
        Args:
            new_state: 目标状态
            **kwargs: 传递给回调函数的参数
            
        Returns:
            bool: 是否转换成功
        """
        if new_state == self.current_state:
            logger.warning(f"Already in state: {new_state}")
            return False
        
        # 查找转换规则
        transition_key = (self.current_state, new_state)
        transition = self.transitions.get(transition_key)
        
        # 如果没有精确匹配，尝试通配符（from_state为None）
        if not transition:
            wildcard_key = (None, new_state)
            transition = self.transitions.get(wildcard_key)
        
        if not transition:
            logger.error(f"No transition defined from {self.current_state} to {new_state}")
            return False
        
        # 检查转换条件
        if not transition.can_transition():
            logger.warning(f"Transition condition not met: {self.current_state} -> {new_state}")
            return False
        
        # 执行转换
        logger.info(f"State transition: {self.current_state} -> {new_state}")
        self.previous_state = self.current_state
        
        # 执行退出回调
        if transition.on_exit:
            transition.on_exit(**kwargs)
        
        # 更新状态
        self.current_state = new_state
        
        # 执行进入回调
        if transition.on_enter:
            transition.on_enter(**kwargs)
        
        return True
    
    def is_in_state(self, state: GamePhase) -> bool:
        """检查当前是否处于指定状态"""
        return self.current_state == state
    
    def is_in_any_of(self, states: list) -> bool:
        """检查当前是否处于指定状态列表中的任意一个"""
        return self.current_state in states
    
    def can_transition_to(self, new_state: GamePhase) -> bool:
        """检查是否可以转换到指定状态"""
        transition_key = (self.current_state, new_state)
        if transition_key in self.transitions:
            return self.transitions[transition_key].can_transition()
        
        # 检查通配符
        wildcard_key = (None, new_state)
        if wildcard_key in self.transitions:
            return self.transitions[wildcard_key].can_transition()
        
        return False
    
    def get_current_state(self) -> GamePhase:
        """获取当前状态"""
        return self.current_state
    
    def get_previous_state(self) -> Optional[GamePhase]:
        """获取前一个状态"""
        return self.previous_state
    
    def reset(self):
        """重置状态机到初始状态"""
        self.previous_state = self.current_state
        self.current_state = GamePhase.INITIALIZING
        logger.info("StateMachine reset to INITIALIZING")
    
    def __repr__(self):
        return f"GameStateMachine(current={self.current_state}, previous={self.previous_state})"

