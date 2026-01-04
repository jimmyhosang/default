"""
Simple pub/sub event bus for decoupling components.
"""
from typing import Callable, Dict, List, Any
import logging
import asyncio

logger = logging.getLogger(__name__)

# Type alias for event handlers
EventHandler = Callable[[Dict[str, Any]], None]
AsyncEventHandler = Callable[[Dict[str, Any]], Any]


class EventBus:
    """
    Simple publish/subscribe event bus.
    Supports both sync and async handlers.
    """
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern for global event bus."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._subscribers: Dict[str, List[Callable]] = {}
        return cls._instance
    
    def subscribe(self, event_type: str, handler: Callable) -> None:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Type of event to listen for.
            handler: Callback function (sync or async).
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)
        logger.debug(f"Subscribed to {event_type}: {handler.__name__}")
    
    def unsubscribe(self, event_type: str, handler: Callable) -> None:
        """
        Unsubscribe from an event type.
        
        Args:
            event_type: Type of event.
            handler: Handler to remove.
        """
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                h for h in self._subscribers[event_type] if h != handler
            ]
            logger.debug(f"Unsubscribed from {event_type}: {handler.__name__}")
    
    def publish(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Publish an event synchronously.
        
        Args:
            event_type: Type of event.
            payload: Event data.
        """
        handlers = self._subscribers.get(event_type, [])
        logger.debug(f"Publishing {event_type} to {len(handlers)} handlers")
        
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    # Schedule async handler
                    asyncio.create_task(handler(payload))
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__}: {e}")
    
    async def publish_async(self, event_type: str, payload: Dict[str, Any]) -> None:
        """
        Publish an event and await all async handlers.
        
        Args:
            event_type: Type of event.
            payload: Event data.
        """
        handlers = self._subscribers.get(event_type, [])
        logger.debug(f"Publishing {event_type} to {len(handlers)} handlers (async)")
        
        tasks = []
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    tasks.append(handler(payload))
                else:
                    handler(payload)
            except Exception as e:
                logger.error(f"Error in handler {handler.__name__}: {e}")
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def clear(self, event_type: str = None) -> None:
        """
        Clear subscribers.
        
        Args:
            event_type: Specific event type to clear, or None for all.
        """
        if event_type:
            self._subscribers[event_type] = []
        else:
            self._subscribers.clear()
        logger.debug(f"Cleared subscribers for: {event_type or 'all'}")


# Global event bus instance
event_bus = EventBus()


# Common event types
class EventTypes:
    """Standard event type constants."""
    # Capture events
    SCREEN_CAPTURED = "capture.screen"
    CLIPBOARD_CHANGED = "capture.clipboard"
    FILE_CHANGED = "capture.file"
    
    # Action events
    ACTION_STARTED = "action.started"
    ACTION_COMPLETED = "action.completed"
    ACTION_FAILED = "action.failed"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow.started"
    WORKFLOW_COMPLETED = "workflow.completed"
    WORKFLOW_FAILED = "workflow.failed"
