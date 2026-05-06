"""
单元测试 - 事件总线系统测试
"""
import pytest
from desktop.events.event_bus import EventBus, Event


@pytest.fixture
def event_bus():
    """创建干净的事件总线实例"""
    EventBus.reset()
    return EventBus.get_instance()


class TestEventBus:
    """事件总线测试类"""
    
    def test_singleton(self):
        """测试单例模式"""
        bus1 = EventBus.get_instance()
        bus2 = EventBus.get_instance()
        assert bus1 is bus2
    
    def test_subscribe_and_emit(self, event_bus):
        """测试订阅和发布事件"""
        received_events = []
        
        def handler(event):
            received_events.append(event)
        
        event_bus.subscribe("test_event", handler)
        event_bus.emit("test_event", {"data": "value"})
        
        assert len(received_events) == 1
        assert received_events[0].event_type == "test_event"
        assert received_events[0].data == {"data": "value"}
    
    def test_unsubscribe(self, event_bus):
        """测试取消订阅"""
        call_count = [0]
        
        def handler(event):
            call_count[0] += 1
        
        event_bus.subscribe("test_event", handler)
        event_bus.emit("test_event")
        assert call_count[0] == 1
        
        event_bus.unsubscribe("test_event", handler)
        event_bus.emit("test_event")
        assert call_count[0] == 1  # 应该不再增加
    
    def test_subscribe_once(self, event_bus):
        """测试一次性订阅"""
        call_count = [0]
        
        def handler(event):
            call_count[0] += 1
        
        event_bus.subscribe_once("test_event", handler)
        
        event_bus.emit("test_event")
        assert call_count[0] == 1
        
        event_bus.emit("test_event")
        assert call_count[0] == 1  # 第二次不应该触发
    
    def test_multiple_handlers(self, event_bus):
        """测试多个处理器"""
        results = []
        
        def handler1(event):
            results.append("handler1")
        
        def handler2(event):
            results.append("handler2")
        
        event_bus.subscribe("test_event", handler1)
        event_bus.subscribe("test_event", handler2)
        
        event_bus.emit("test_event")
        
        assert len(results) == 2
        assert "handler1" in results
        assert "handler2" in results
    
    def test_handler_priority(self, event_bus):
        """测试处理器优先级"""
        execution_order = []
        
        def low_priority(event):
            execution_order.append("low")
        
        def high_priority(event):
            execution_order.append("high")
        
        event_bus.subscribe("test_event", low_priority, priority=1)
        event_bus.subscribe("test_event", high_priority, priority=10)
        
        event_bus.emit("test_event")
        
        assert execution_order == ["high", "low"]
    
    def test_stop_propagation(self, event_bus):
        """测试停止事件传播"""
        results = []
        
        def handler1(event):
            results.append("handler1")
            event.stop_propagation()
        
        def handler2(event):
            results.append("handler2")
        
        event_bus.subscribe("test_event", handler1)
        event_bus.subscribe("test_event", handler2)
        
        event_bus.emit("test_event")
        
        assert results == ["handler1"]
        assert "handler2" not in results
    
    def test_handler_exception_handling(self, event_bus):
        """测试处理器异常处理"""
        results = []
        
        def failing_handler(event):
            raise ValueError("Test error")
        
        def normal_handler(event):
            results.append("executed")
        
        event_bus.subscribe("test_event", failing_handler)
        event_bus.subscribe("test_event", normal_handler)
        
        # 不应该抛出异常
        event_bus.emit("test_event")
        
        # 第二个处理器仍应执行
        assert "executed" in results
    
    def test_has_subscribers(self, event_bus):
        """测试是否有订阅者"""
        def handler(event):
            pass
        
        assert not event_bus.has_subscribers("test_event")
        
        event_bus.subscribe("test_event", handler)
        assert event_bus.has_subscribers("test_event")
        
        event_bus.unsubscribe("test_event", handler)
        assert not event_bus.has_subscribers("test_event")
    
    def test_clear_handlers(self, event_bus):
        """测试清理事件处理器"""
        def handler(event):
            pass
        
        event_bus.subscribe("event1", handler)
        event_bus.subscribe("event2", handler)
        
        event_bus.clear("event1")
        assert not event_bus.has_subscribers("event1")
        assert event_bus.has_subscribers("event2")
        
        event_bus.clear()
        assert not event_bus.has_subscribers("event2")
    
    def test_event_history(self, event_bus):
        """测试事件历史"""
        event_bus.emit("event1", {"key": "value1"})
        event_bus.emit("event2", {"key": "value2"})
        
        history = event_bus.get_event_history()
        
        assert len(history) == 2
        assert history[0].event_type == "event1"
        assert history[1].event_type == "event2"
    
    def test_event_history_limit(self, event_bus):
        """测试事件历史限制"""
        for i in range(15):
            event_bus.emit(f"event_{i}")
        
        history = event_bus.get_event_history(limit=10)
        assert len(history) == 10
    
    def test_get_stats(self, event_bus):
        """测试获取统计信息"""
        def handler(event):
            pass
        
        event_bus.subscribe("event1", handler)
        event_bus.subscribe("event1", handler)
        event_bus.subscribe("event2", handler)
        
        stats = event_bus.get_stats()
        
        assert stats['total_event_types'] == 2
        assert stats['total_handlers'] == 3
    
    def test_invalid_handler_type(self, event_bus):
        """测试无效的处理器类型"""
        with pytest.raises(TypeError):
            event_bus.subscribe("test_event", "not_a_function")
    
    def test_event_repr(self):
        """测试事件字符串表示"""
        event = Event("test_type", {"key": "value"})
        assert "test_type" in repr(event)
        assert "key" in repr(event)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

