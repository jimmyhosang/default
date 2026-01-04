"""
Model Router for selecting the appropriate LLM based on task complexity.
"""
from typing import Dict, Any

class ModelRouter:
    """
    Decides which model to use for a given task.
    """
    
    # Default model configuration
    DEFAULT_CONFIG = {
        "fast": "llama3.2",      # Small, fast, local
        "balanced": "mistral",   # Medium, local
        "powerful": "claude-3-5-sonnet-20241022" # Large, cloud/local
    }
    
    def __init__(self, config: Dict[str, str] = None):
        """
        Initialize router with model config.
        
        Args:
            config: Dict mapping complexity ('fast', 'balanced', 'powerful') to model names.
        """
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
    def route(self, complexity: str = "balanced") -> str:
        """
        Get the model name for the given complexity.
        
        Args:
            complexity: 'fast', 'balanced', or 'powerful'.
            
        Returns:
            Model name string.
        """
        if complexity not in self.config:
            # Fallback to balanced if unknown complexity
            return self.config["balanced"]
            
        return self.config[complexity]
