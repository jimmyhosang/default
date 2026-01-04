"""
Agent Orchestrator - Central Controller for AI Reasoning and Action

This module provides the main orchestration layer that:
1. Receives user intent/requests
2. Retrieves relevant context from semantic store
3. Plans multi-step actions
4. Executes actions with appropriate tools
5. Learns from outcomes

The orchestrator bridges the System of Record, System of Action, and System of Thought.
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from enum import Enum
import logging
import json
import asyncio

from src.thought.llm_client import LLMClient
from src.thought.router import ModelRouter
from src.store.semantic_store import SemanticStore
from src.action.executor import ActionExecutor

logger = logging.getLogger(__name__)


class TaskComplexity(Enum):
    """Task complexity levels for model routing."""
    SIMPLE = "simple"      # Simple lookup, classification
    MODERATE = "moderate"  # Analysis, summarization
    COMPLEX = "complex"    # Multi-step reasoning, planning


@dataclass
class PlanStep:
    """A single step in an execution plan."""
    step_id: int
    action: str
    description: str
    params: Dict[str, Any] = field(default_factory=dict)
    requires_approval: bool = False
    depends_on: List[int] = field(default_factory=list)
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    error: Optional[str] = None


@dataclass
class ExecutionPlan:
    """A complete execution plan for a user request."""
    goal: str
    steps: List[PlanStep] = field(default_factory=list)
    context: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "planning"  # planning, executing, completed, failed
    final_response: Optional[str] = None


class Orchestrator:
    """
    Central controller for the AI agent.

    Responsibilities:
    - Parse user intent
    - Retrieve relevant context
    - Plan multi-step actions
    - Execute with appropriate tools
    - Generate final response
    """

    # Available tools/actions the agent can use
    AVAILABLE_TOOLS = {
        "search": {
            "description": "Search captured content for relevant information",
            "params": ["query"],
            "requires_approval": False
        },
        "semantic_search": {
            "description": "Search using semantic similarity (meaning-based)",
            "params": ["query"],
            "requires_approval": False
        },
        "summarize": {
            "description": "Summarize a piece of content",
            "params": ["content"],
            "requires_approval": False
        },
        "open_file": {
            "description": "Open a file on the user's system",
            "params": ["path"],
            "requires_approval": True
        },
        "list_files": {
            "description": "List files in a directory",
            "params": ["directory"],
            "requires_approval": False
        },
        "get_entities": {
            "description": "Get extracted entities (people, organizations, etc.)",
            "params": ["entity_type"],
            "requires_approval": False
        },
        "answer": {
            "description": "Generate an answer using available context",
            "params": ["question", "context"],
            "requires_approval": False
        }
    }

    def __init__(
        self,
        store: Optional[SemanticStore] = None,
        executor: Optional[ActionExecutor] = None
    ):
        """
        Initialize orchestrator.

        Args:
            store: Semantic store for context retrieval
            executor: Action executor for running tools
        """
        self.llm = LLMClient()
        self.router = ModelRouter()
        self.store = store or SemanticStore()
        self.executor = executor or ActionExecutor()

        # Conversation history for context
        self.conversation_history: List[Dict[str, str]] = []

    async def process(self, user_input: str) -> str:
        """
        Process user input and return a response.

        This is the main entry point that orchestrates:
        1. Intent classification
        2. Context retrieval
        3. Planning
        4. Execution
        5. Response generation

        Args:
            user_input: The user's request or question

        Returns:
            Final response string
        """
        logger.info(f"Processing: {user_input[:100]}...")

        # Add to conversation history
        self.conversation_history.append({"role": "user", "content": user_input})

        try:
            # Step 1: Classify complexity and intent
            complexity = await self._classify_complexity(user_input)
            logger.info(f"Classified complexity: {complexity}")

            # Step 2: Retrieve relevant context
            context = await self._retrieve_context(user_input)
            logger.info(f"Retrieved {len(context)} context items")

            # Step 3: Generate plan
            plan = await self._create_plan(user_input, context, complexity)
            logger.info(f"Created plan with {len(plan.steps)} steps")

            # Step 4: Execute plan
            await self._execute_plan(plan)

            # Step 5: Generate final response
            response = await self._generate_response(plan)

            # Add to history
            self.conversation_history.append({"role": "assistant", "content": response})

            return response

        except Exception as e:
            logger.error(f"Orchestrator error: {e}", exc_info=True)
            error_response = f"I encountered an error processing your request: {str(e)}"
            self.conversation_history.append({"role": "assistant", "content": error_response})
            return error_response

    async def _classify_complexity(self, user_input: str) -> TaskComplexity:
        """
        Classify the complexity of a user request.

        Uses heuristics and optionally LLM for complex cases.
        """
        input_lower = user_input.lower()

        # Simple heuristics first
        simple_patterns = [
            "what is", "who is", "when", "where",
            "find", "search", "show me", "list"
        ]

        complex_patterns = [
            "analyze", "compare", "summarize all", "create a plan",
            "help me", "how should i", "what should"
        ]

        # Check for simple patterns
        if any(pattern in input_lower for pattern in simple_patterns):
            if len(user_input) < 50:
                return TaskComplexity.SIMPLE

        # Check for complex patterns
        if any(pattern in input_lower for pattern in complex_patterns):
            return TaskComplexity.COMPLEX

        # Default to moderate
        return TaskComplexity.MODERATE

    async def _retrieve_context(self, user_input: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Retrieve relevant context from the semantic store.
        """
        try:
            # Try semantic search first
            results = self.store.semantic_search(user_input, limit=limit)

            if not results:
                # Fall back to text search
                results = self.store.search(user_input, limit=limit)

            return results
        except Exception as e:
            logger.warning(f"Context retrieval failed: {e}")
            return []

    async def _create_plan(
        self,
        user_input: str,
        context: List[Dict[str, Any]],
        complexity: TaskComplexity
    ) -> ExecutionPlan:
        """
        Create an execution plan for the user request.

        For simple requests, creates a single-step plan.
        For complex requests, uses LLM to generate multi-step plan.
        """
        plan = ExecutionPlan(goal=user_input, context=context)

        if complexity == TaskComplexity.SIMPLE:
            # Simple: just answer using context
            plan.steps.append(PlanStep(
                step_id=1,
                action="answer",
                description="Generate answer from context",
                params={"question": user_input}
            ))

        elif complexity == TaskComplexity.MODERATE:
            # Moderate: search + answer
            plan.steps.append(PlanStep(
                step_id=1,
                action="search",
                description="Search for relevant information",
                params={"query": user_input}
            ))
            plan.steps.append(PlanStep(
                step_id=2,
                action="answer",
                description="Generate answer from search results",
                params={"question": user_input},
                depends_on=[1]
            ))

        else:
            # Complex: use LLM to generate plan
            plan = await self._generate_llm_plan(user_input, context)

        plan.status = "ready"
        return plan

    async def _generate_llm_plan(
        self,
        user_input: str,
        context: List[Dict[str, Any]]
    ) -> ExecutionPlan:
        """
        Use LLM to generate a multi-step execution plan.
        """
        plan = ExecutionPlan(goal=user_input, context=context)

        # Format available tools for LLM
        tools_desc = "\n".join([
            f"- {name}: {info['description']} (params: {info['params']})"
            for name, info in self.AVAILABLE_TOOLS.items()
        ])

        # Format context
        context_str = ""
        if context:
            context_str = "\n".join([
                f"- {c.get('content', '')[:200]}..."
                for c in context[:3]
            ])

        system_prompt = """You are a task planning assistant. Given a user request, create a step-by-step plan using available tools.

Available tools:
{tools}

Output your plan as JSON with this structure:
{{
    "steps": [
        {{"action": "tool_name", "description": "what this step does", "params": {{"key": "value"}}}},
        ...
    ]
}}

Keep plans concise (1-5 steps). Only use tools from the available list.""".format(tools=tools_desc)

        user_prompt = f"""User request: {user_input}

Relevant context:
{context_str if context_str else "No context available."}

Create a plan to fulfill this request."""

        try:
            model = self.router.route("powerful")
            result = await self.llm.generate(
                prompt=user_prompt,
                model=model,
                system=system_prompt,
                json_mode=True,
                temperature=0.3
            )

            # Parse the plan
            plan_data = json.loads(result["content"])

            for i, step in enumerate(plan_data.get("steps", []), 1):
                tool_name = step.get("action", "answer")
                tool_info = self.AVAILABLE_TOOLS.get(tool_name, {})

                plan.steps.append(PlanStep(
                    step_id=i,
                    action=tool_name,
                    description=step.get("description", ""),
                    params=step.get("params", {}),
                    requires_approval=tool_info.get("requires_approval", False),
                    depends_on=[i-1] if i > 1 else []
                ))

        except Exception as e:
            logger.warning(f"LLM planning failed: {e}, falling back to simple plan")
            plan.steps.append(PlanStep(
                step_id=1,
                action="answer",
                description="Generate answer directly",
                params={"question": user_input}
            ))

        return plan

    async def _execute_plan(self, plan: ExecutionPlan) -> None:
        """
        Execute all steps in a plan.
        """
        plan.status = "executing"

        for step in plan.steps:
            # Check dependencies
            deps_complete = all(
                plan.steps[dep_id - 1].status == "completed"
                for dep_id in step.depends_on
                if dep_id <= len(plan.steps)
            )

            if not deps_complete:
                step.status = "failed"
                step.error = "Dependencies not met"
                continue

            step.status = "running"

            try:
                result = await self._execute_step(step, plan)
                step.result = result
                step.status = "completed"
            except Exception as e:
                step.status = "failed"
                step.error = str(e)
                logger.error(f"Step {step.step_id} failed: {e}")

        # Determine overall status
        if all(s.status == "completed" for s in plan.steps):
            plan.status = "completed"
        elif any(s.status == "failed" for s in plan.steps):
            plan.status = "partial"
        else:
            plan.status = "completed"

    async def _execute_step(self, step: PlanStep, plan: ExecutionPlan) -> Any:
        """
        Execute a single plan step.
        """
        action = step.action
        params = step.params

        if action == "search":
            query = params.get("query", plan.goal)
            return self.store.search(query, limit=10)

        elif action == "semantic_search":
            query = params.get("query", plan.goal)
            return self.store.semantic_search(query, limit=10)

        elif action == "get_entities":
            entity_type = params.get("entity_type")
            return self.store.get_entities(entity_type=entity_type, limit=50)

        elif action == "summarize":
            content = params.get("content", "")
            # Get from previous step if not provided
            if not content and step.depends_on:
                prev_step = plan.steps[step.depends_on[0] - 1]
                if prev_step.result:
                    content = str(prev_step.result)[:2000]

            model = self.router.route("balanced")
            result = await self.llm.generate(
                prompt=f"Summarize the following:\n\n{content}",
                model=model,
                system="Provide a concise summary.",
                temperature=0.3
            )
            return result["content"]

        elif action == "answer":
            # Collect context from previous steps and plan context
            context_parts = []

            # From previous steps
            for s in plan.steps:
                if s.step_id < step.step_id and s.result:
                    if isinstance(s.result, list):
                        for item in s.result[:5]:
                            if isinstance(item, dict):
                                context_parts.append(item.get("content", str(item))[:500])
                    else:
                        context_parts.append(str(s.result)[:500])

            # From plan context
            for ctx in plan.context[:3]:
                context_parts.append(ctx.get("content", "")[:500])

            context_str = "\n\n".join(context_parts) if context_parts else "No specific context available."

            model = self.router.route("balanced")
            result = await self.llm.generate(
                prompt=f"""Question: {params.get('question', plan.goal)}

Context:
{context_str}

Provide a helpful, accurate answer based on the available context.""",
                model=model,
                system="You are a helpful assistant. Answer based on the provided context. If the context doesn't contain enough information, say so.",
                temperature=0.5
            )
            return result["content"]

        elif action == "list_files":
            directory = params.get("directory", "")
            result = await self.executor.execute({
                "category": "file",
                "action": "list",
                "params": {"path": directory}
            })
            return result

        elif action == "open_file":
            # This requires approval - for now, just note it
            path = params.get("path", "")
            return f"Would open file: {path} (requires approval)"

        else:
            return f"Unknown action: {action}"

    async def _generate_response(self, plan: ExecutionPlan) -> str:
        """
        Generate the final response based on plan execution.
        """
        # Find the answer step or last completed step
        answer_step = None
        for step in reversed(plan.steps):
            if step.action == "answer" and step.status == "completed":
                answer_step = step
                break
            elif step.status == "completed":
                answer_step = step

        if answer_step and answer_step.result:
            if isinstance(answer_step.result, str):
                return answer_step.result
            else:
                return str(answer_step.result)

        # If no good result, generate a summary
        results = [s.result for s in plan.steps if s.result]
        if results:
            return f"Based on my analysis: {str(results[0])[:500]}"

        return "I wasn't able to find enough information to answer your request."

    def clear_history(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []

    def get_history(self) -> List[Dict[str, str]]:
        """Get conversation history."""
        return self.conversation_history.copy()
