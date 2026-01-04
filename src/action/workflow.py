from typing import List, Dict, Any
from .executor import ActionExecutor

class WorkflowEngine:
    """
    Orchestrates sequences of actions.
    """
    def __init__(self, executor: ActionExecutor):
        self.executor = executor

    async def run_workflow(self, workflow_steps: List[Dict[str, Any]]) -> List[Any]:
        """
        Run a sequence of actions.

        Args:
            workflow_steps: List of action definitions.

        Returns:
            List of results for each step.
        """
        results = []
        for step in workflow_steps:
            result = await self.executor.execute(step)
            results.append(result)
        return results
