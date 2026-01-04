from typing import Any, Dict, Optional
import logging

from .event_bus import event_bus, EventTypes
from .tools.file_tools import FileTools
from .tools.desktop_tools import DesktopTools, PYAUTOGUI_AVAILABLE
from .tools.browser_tools import BrowserTools, PLAYWRIGHT_AVAILABLE

logger = logging.getLogger(__name__)


class ActionExecutor:
    """
    Secure executor for automated actions.
    Responsible for:
    - Sandboxing (where possible)
    - Permission checks
    - Logging execution
    - Routing to appropriate tool
    """
    
    # Permission levels required for each action type
    PERMISSION_REQUIREMENTS = {
        "file": "safe",
        "desktop": "user-approved",
        "browser": "safe",
    }
    
    def __init__(self, permission_level: str = "safe"):
        """
        Initialize the ActionExecutor.

        Args:
            permission_level: The permission level for execution ("safe", "user-approved", "admin").
        """
        self.permission_level = permission_level
        self._file_tools = FileTools()
        self._desktop_tools = None
        self._browser_tools = None
    
    def _check_permission(self, action_type: str) -> bool:
        """Check if current permission level allows the action."""
        required = self.PERMISSION_REQUIREMENTS.get(action_type, "admin")
        levels = ["safe", "user-approved", "admin"]
        return levels.index(self.permission_level) >= levels.index(required)

    async def execute(self, action_def: Dict[str, Any]) -> Any:
        """
        Execute an action based on the definition.
        
        Args:
            action_def: Dictionary defining the action to execute.
                        Must contain 'type' and 'params'.
                        Example: {"type": "file.create", "params": {"path": "...", "content": "..."}}
                        
        Returns:
            Result of the action execution.
            
        Raises:
            ValueError: If action type is unknown or not permitted.
            PermissionError: If permission level is insufficient.
        """
        action_type = action_def.get("type", "")
        params = action_def.get("params", {})
        
        # Determine category and method
        parts = action_type.split(".", 1)
        if len(parts) != 2:
            raise ValueError(f"Invalid action type format: {action_type}. Expected 'category.method'")
        
        category, method = parts
        
        # Check permissions
        if not self._check_permission(category):
            raise PermissionError(f"Permission level '{self.permission_level}' cannot execute '{category}' actions")
        
        # Emit start event
        event_bus.publish(EventTypes.ACTION_STARTED, {
            "type": action_type,
            "params": params,
        })
        
        try:
            result = await self._dispatch(category, method, params)
            
            # Emit completion event
            event_bus.publish(EventTypes.ACTION_COMPLETED, {
                "type": action_type,
                "result": result,
            })
            
            return result
            
        except Exception as e:
            # Emit failure event
            event_bus.publish(EventTypes.ACTION_FAILED, {
                "type": action_type,
                "error": str(e),
            })
            raise

    async def _dispatch(self, category: str, method: str, params: Dict[str, Any]) -> Any:
        """Route action to appropriate tool."""
        
        if category == "file":
            return self._execute_file_action(method, params)
        
        elif category == "desktop":
            return self._execute_desktop_action(method, params)
        
        elif category == "browser":
            return await self._execute_browser_action(method, params)
        
        else:
            raise ValueError(f"Unknown action category: {category}")

    def _execute_file_action(self, method: str, params: Dict[str, Any]) -> Any:
        """Execute file-based actions."""
        handler = getattr(self._file_tools, method, None)
        if not handler:
            raise ValueError(f"Unknown file action: {method}")
        return handler(**params)

    def _execute_desktop_action(self, method: str, params: Dict[str, Any]) -> Any:
        """Execute desktop automation actions."""
        if not PYAUTOGUI_AVAILABLE:
            raise RuntimeError("PyAutoGUI is not available")
        
        if self._desktop_tools is None:
            self._desktop_tools = DesktopTools()
        
        handler = getattr(self._desktop_tools, method, None)
        if not handler:
            raise ValueError(f"Unknown desktop action: {method}")
        return handler(**params)

    async def _execute_browser_action(self, method: str, params: Dict[str, Any]) -> Any:
        """Execute browser automation actions."""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright is not available")
        
        if self._browser_tools is None:
            self._browser_tools = BrowserTools()
        
        handler = getattr(self._browser_tools, method, None)
        if not handler:
            raise ValueError(f"Unknown browser action: {method}")
        return await handler(**params)
