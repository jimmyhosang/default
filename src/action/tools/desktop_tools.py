"""
Desktop automation tools using PyAutoGUI.
"""
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False
    logger.warning("PyAutoGUI not available. Desktop automation disabled.")


class DesktopTools:
    """
    Desktop automation for mouse/keyboard control.
    Requires explicit user approval for most actions.
    """
    
    def __init__(self, failsafe: bool = True):
        """
        Initialize DesktopTools.
        
        Args:
            failsafe: If True, moving mouse to corner aborts actions.
        """
        if not PYAUTOGUI_AVAILABLE:
            raise ImportError("PyAutoGUI is required for desktop automation")
        
        pyautogui.FAILSAFE = failsafe
        pyautogui.PAUSE = 0.1  # Small delay between actions
    
    def click(self, x: int, y: int, button: str = "left", clicks: int = 1) -> dict:
        """
        Click at specified coordinates.
        
        Args:
            x: X coordinate.
            y: Y coordinate.
            button: Mouse button ("left", "right", "middle").
            clicks: Number of clicks.
            
        Returns:
            Dict with status.
        """
        pyautogui.click(x, y, button=button, clicks=clicks)
        logger.info(f"Clicked at ({x}, {y}) with {button} button, {clicks} time(s)")
        return {"status": "success", "action": "click", "x": x, "y": y}

    def type_text(self, text: str, interval: float = 0.05) -> dict:
        """
        Type text using keyboard.
        
        Args:
            text: Text to type.
            interval: Delay between keystrokes.
            
        Returns:
            Dict with status.
        """
        pyautogui.typewrite(text, interval=interval)
        logger.info(f"Typed text: {text[:50]}...")
        return {"status": "success", "action": "type", "length": len(text)}

    def hotkey(self, *keys: str) -> dict:
        """
        Press a keyboard shortcut.
        
        Args:
            *keys: Keys to press (e.g., "ctrl", "c").
            
        Returns:
            Dict with status.
        """
        pyautogui.hotkey(*keys)
        logger.info(f"Pressed hotkey: {'+'.join(keys)}")
        return {"status": "success", "action": "hotkey", "keys": list(keys)}

    def screenshot(self, region: Optional[Tuple[int, int, int, int]] = None) -> dict:
        """
        Take a screenshot.
        
        Args:
            region: Optional (x, y, width, height) tuple for partial screenshot.
            
        Returns:
            Dict with PIL Image.
        """
        img = pyautogui.screenshot(region=region)
        logger.info(f"Screenshot taken: {img.size}")
        return {"status": "success", "action": "screenshot", "size": img.size, "image": img}

    def locate_on_screen(self, image_path: str, confidence: float = 0.9) -> dict:
        """
        Find an image on screen.
        
        Args:
            image_path: Path to the image to find.
            confidence: Match confidence (0-1).
            
        Returns:
            Dict with location or None if not found.
        """
        try:
            location = pyautogui.locateOnScreen(image_path, confidence=confidence)
            if location:
                logger.info(f"Found image at: {location}")
                return {"status": "success", "found": True, "location": location}
            else:
                return {"status": "success", "found": False, "location": None}
        except pyautogui.ImageNotFoundException:
            return {"status": "success", "found": False, "location": None}

    def move_mouse(self, x: int, y: int, duration: float = 0.25) -> dict:
        """
        Move mouse to coordinates.
        
        Args:
            x: X coordinate.
            y: Y coordinate.
            duration: Time to move (seconds).
            
        Returns:
            Dict with status.
        """
        pyautogui.moveTo(x, y, duration=duration)
        logger.info(f"Moved mouse to ({x}, {y})")
        return {"status": "success", "action": "move", "x": x, "y": y}

    def get_mouse_position(self) -> dict:
        """
        Get current mouse position.
        
        Returns:
            Dict with x and y coordinates.
        """
        pos = pyautogui.position()
        return {"status": "success", "x": pos.x, "y": pos.y}

    def get_screen_size(self) -> dict:
        """
        Get screen dimensions.
        
        Returns:
            Dict with width and height.
        """
        size = pyautogui.size()
        return {"status": "success", "width": size.width, "height": size.height}
