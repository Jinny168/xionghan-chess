"""
事件总线系统 - 实现观察者模式，解耦组件间通信
"""
import logging
from typing import Callable, Dict, List, Any, Optional
from collections import defaultdict

logger = logging.getLogger(__name__)


class Event:
    """事件基类"""
    
    def __init__(self, event_type: str, data: Optional[Dict[str, Any]] = None):
        self.event_type = event_type
        self.data = data or {}
        self.handled = False
    
    def stop_propagation(self):
        """停止事件传播"""
        self.handled = True
    
    def __repr__(self):
        return f"Event(type={self.event_type}, data={self.data})"


class EventBus:
    """
    事件总线 - 单例模式
    用于组件间的松耦合通信
    """
    
    _instance: Optional['EventBus'] = None
    _initialized: bool = False
    
    def __new__(cls) -> 'EventBus':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            # 存储事件处理器: {event_type: [handler1, handler2, ...]}
            self._handlers: Dict[str, List[Callable]] = defaultdict(list)
            # 存储一次性处理器
            self._once_handlers: Dict[str, List[Callable]] = defaultdict(list)
            # 事件历史记录（可选，用于调试）
            self._event_history: List[Event] = []
            self._max_history_size: int = 100
            self._initialized = True
            logger.info("EventBus initialized")
    
    @classmethod
    def get_instance(cls) -> 'EventBus':
        """获取事件总线单例实例"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """重置事件总线（主要用于测试）"""
        if cls._instance:
            cls._instance._handlers.clear()
            cls._instance._once_handlers.clear()
            cls._instance._event_history.clear()
    
    def subscribe(self, event_type: str, handler: Callable[[Event], None], priority: int = 0) -> None:
        """
        订阅事件
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数，接收Event对象作为参数
            priority: 优先级（数值越大越先执行）
        """
        if not callable(handler):
            raise TypeError(f"Handler must be callable, got {type(handler)}")
        
        # 存储处理器及其优先级
        handler_info = {'handler': handler, 'priority': priority}
        self._handlers[event_type].append(handler_info)
        # 按优先级排序（降序）
        self._handlers[event_type].sort(key=lambda x: x['priority'], reverse=True)
        
        logger.debug(f"Subscribed to event '{event_type}' with priority {priority}")
    
    def unsubscribe(self, event_type: str, handler: Callable[[Event], None]) -> bool:
        """
        取消订阅事件
        
        Args:
            event_type: 事件类型
            handler: 要取消的处理函数
            
        Returns:
            bool: 是否成功取消订阅
        """
        handlers = self._handlers.get(event_type, [])
        original_count = len(handlers)
        
        self._handlers[event_type] = [
            h for h in handlers if h['handler'] != handler
        ]
        
        removed = len(self._handlers[event_type]) < original_count
        if removed:
            logger.debug(f"Unsubscribed from event '{event_type}'")
        
        return removed
    
    def subscribe_once(self, event_type: str, handler: Callable[[Event], None]) -> None:
        """
        订阅一次性事件（触发后自动取消订阅）
        
        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        self._once_handlers[event_type].append(handler)
        logger.debug(f"Subscribed once to event '{event_type}'")
    
    def emit(self, event_type: str, data: Optional[Dict[str, Any]] = None) -> Event:
        """
        发布事件
        
        Args:
            event_type: 事件类型
            data: 事件数据
            
        Returns:
            Event: 发布的事件对象
        """
        event = Event(event_type, data)
        
        # 记录事件历史
        self._event_history.append(event)
        if len(self._event_history) > self._max_history_size:
            self._event_history.pop(0)
        
        logger.debug(f"Emitting event: {event}")
        
        # 收集所有需要执行的处理器
        handlers_to_execute = []
        
        # 添加常规处理器
        if event_type in self._handlers:
            handlers_to_execute.extend([
                h['handler'] for h in self._handlers[event_type]
            ])
        
        # 添加一次性处理器
        if event_type in self._once_handlers:
            handlers_to_execute.extend(self._once_handlers[event_type])
            # 清除一次性处理器
            self._once_handlers[event_type].clear()
        
        # 执行所有处理器
        for handler in handlers_to_execute:
            if event.handled:
                break
            try:
                handler(event)
            except Exception as e:
                logger.error(f"Error in event handler for '{event_type}': {e}", exc_info=True)
        
        return event
    
    def clear(self, event_type: Optional[str] = None) -> None:
        """
        清理事件处理器
        
        Args:
            event_type: 如果指定，只清理该类型的事件；否则清理所有
        """
        if event_type:
            self._handlers.pop(event_type, None)
            self._once_handlers.pop(event_type, None)
            logger.debug(f"Cleared all handlers for event '{event_type}'")
        else:
            self._handlers.clear()
            self._once_handlers.clear()
            logger.info("Cleared all event handlers")
    
    def has_subscribers(self, event_type: str) -> bool:
        """
        检查是否有订阅者
        
        Args:
            event_type: 事件类型
            
        Returns:
            bool: 是否有订阅者
        """
        return (
            len(self._handlers.get(event_type, [])) > 0 or
            len(self._once_handlers.get(event_type, [])) > 0
        )
    
    def get_event_history(self, limit: int = 10) -> List[Event]:
        """
        获取事件历史
        
        Args:
            limit: 返回的历史记录数量
            
        Returns:
            List[Event]: 事件历史列表
        """
        return self._event_history[-limit:]
    
    def get_stats(self) -> Dict[str, int]:
        """
        获取事件总线统计信息
        
        Returns:
            Dict: 统计信息
        """
        return {
            'total_event_types': len(self._handlers),
            'total_handlers': sum(len(handlers) for handlers in self._handlers.values()),
            'once_handlers': sum(len(handlers) for handlers in self._once_handlers.values()),
            'history_size': len(self._event_history)
        }


# 全局事件总线实例
event_bus = EventBus.get_instance()

