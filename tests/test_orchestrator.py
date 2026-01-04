"""
Tests for the Agent Orchestrator module.
"""

import pytest
import json
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from src.agents.orchestrator import (
    Orchestrator,
    TaskComplexity,
    PlanStep,
    ExecutionPlan,
)


class TestTaskComplexity:
    """Tests for TaskComplexity enum."""

    def test_complexity_values(self):
        """Test complexity enum values."""
        assert TaskComplexity.SIMPLE.value == "simple"
        assert TaskComplexity.MODERATE.value == "moderate"
        assert TaskComplexity.COMPLEX.value == "complex"


class TestPlanStep:
    """Tests for PlanStep dataclass."""

    def test_default_values(self):
        """Test default PlanStep values."""
        step = PlanStep(
            step_id=1,
            action="search",
            description="Test step"
        )

        assert step.step_id == 1
        assert step.action == "search"
        assert step.description == "Test step"
        assert step.params == {}
        assert step.requires_approval is False
        assert step.depends_on == []
        assert step.status == "pending"
        assert step.result is None
        assert step.error is None

    def test_custom_values(self):
        """Test PlanStep with custom values."""
        step = PlanStep(
            step_id=2,
            action="open_file",
            description="Open document",
            params={"path": "/test/file.txt"},
            requires_approval=True,
            depends_on=[1],
            status="running"
        )

        assert step.requires_approval is True
        assert step.depends_on == [1]
        assert step.params["path"] == "/test/file.txt"


class TestExecutionPlan:
    """Tests for ExecutionPlan dataclass."""

    def test_default_values(self):
        """Test default ExecutionPlan values."""
        plan = ExecutionPlan(goal="Test goal")

        assert plan.goal == "Test goal"
        assert plan.steps == []
        assert plan.context == []
        assert plan.status == "planning"
        assert plan.final_response is None

    def test_with_steps(self):
        """Test ExecutionPlan with steps."""
        step1 = PlanStep(step_id=1, action="search", description="Search")
        step2 = PlanStep(step_id=2, action="answer", description="Answer")

        plan = ExecutionPlan(
            goal="Find and answer",
            steps=[step1, step2]
        )

        assert len(plan.steps) == 2
        assert plan.steps[0].action == "search"
        assert plan.steps[1].action == "answer"


class TestOrchestratorInit:
    """Tests for Orchestrator initialization."""

    @patch('src.agents.orchestrator.LLMClient')
    @patch('src.agents.orchestrator.ModelRouter')
    @patch('src.agents.orchestrator.SemanticStore')
    @patch('src.agents.orchestrator.ActionExecutor')
    def test_default_init(self, mock_executor, mock_store, mock_router, mock_llm):
        """Test Orchestrator initializes with defaults."""
        orchestrator = Orchestrator()

        assert orchestrator.llm is not None
        assert orchestrator.router is not None
        assert orchestrator.store is not None
        assert orchestrator.executor is not None
        assert orchestrator.conversation_history == []

    @patch('src.agents.orchestrator.LLMClient')
    @patch('src.agents.orchestrator.ModelRouter')
    def test_custom_store_and_executor(self, mock_router, mock_llm):
        """Test Orchestrator with custom store and executor."""
        mock_store = MagicMock()
        mock_exec = MagicMock()

        orchestrator = Orchestrator(store=mock_store, executor=mock_exec)

        assert orchestrator.store is mock_store
        assert orchestrator.executor is mock_exec


class TestComplexityClassification:
    """Tests for complexity classification."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch('src.agents.orchestrator.LLMClient'), \
             patch('src.agents.orchestrator.ModelRouter'), \
             patch('src.agents.orchestrator.SemanticStore'), \
             patch('src.agents.orchestrator.ActionExecutor'):
            return Orchestrator()

    @pytest.mark.asyncio
    async def test_simple_queries(self, orchestrator):
        """Test simple query classification."""
        simple_queries = [
            "what is python",
            "who is John",
            "find files",
            "search docs",
            "list items"
        ]

        for query in simple_queries:
            complexity = await orchestrator._classify_complexity(query)
            assert complexity == TaskComplexity.SIMPLE, f"'{query}' should be SIMPLE"

    @pytest.mark.asyncio
    async def test_complex_queries(self, orchestrator):
        """Test complex query classification."""
        complex_queries = [
            "analyze the sales data and compare trends",
            "help me create a marketing plan",
            "how should I structure this project",
            "summarize all documents from last month"
        ]

        for query in complex_queries:
            complexity = await orchestrator._classify_complexity(query)
            assert complexity == TaskComplexity.COMPLEX, f"'{query}' should be COMPLEX"

    @pytest.mark.asyncio
    async def test_moderate_queries(self, orchestrator):
        """Test moderate query classification."""
        moderate_queries = [
            "explain this code block in detail",
            "what are the key points from yesterday's meeting"
        ]

        for query in moderate_queries:
            complexity = await orchestrator._classify_complexity(query)
            assert complexity == TaskComplexity.MODERATE, f"'{query}' should be MODERATE"


class TestContextRetrieval:
    """Tests for context retrieval."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch('src.agents.orchestrator.LLMClient'), \
             patch('src.agents.orchestrator.ModelRouter'), \
             patch('src.agents.orchestrator.SemanticStore') as mock_store_class, \
             patch('src.agents.orchestrator.ActionExecutor'):
            orchestrator = Orchestrator()
            orchestrator.store = MagicMock()
            return orchestrator

    @pytest.mark.asyncio
    async def test_semantic_search_success(self, orchestrator):
        """Test successful semantic search."""
        orchestrator.store.semantic_search.return_value = [
            {"content": "Result 1"},
            {"content": "Result 2"}
        ]

        results = await orchestrator._retrieve_context("test query")

        assert len(results) == 2
        orchestrator.store.semantic_search.assert_called_once_with("test query", limit=5)

    @pytest.mark.asyncio
    async def test_fallback_to_text_search(self, orchestrator):
        """Test fallback to text search when semantic fails."""
        orchestrator.store.semantic_search.return_value = []
        orchestrator.store.search.return_value = [{"content": "Text result"}]

        results = await orchestrator._retrieve_context("test query")

        assert len(results) == 1
        orchestrator.store.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_context_retrieval_error(self, orchestrator):
        """Test handling of context retrieval errors."""
        orchestrator.store.semantic_search.side_effect = Exception("DB error")

        results = await orchestrator._retrieve_context("test query")

        assert results == []


class TestPlanCreation:
    """Tests for plan creation."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch('src.agents.orchestrator.LLMClient'), \
             patch('src.agents.orchestrator.ModelRouter'), \
             patch('src.agents.orchestrator.SemanticStore'), \
             patch('src.agents.orchestrator.ActionExecutor'):
            return Orchestrator()

    @pytest.mark.asyncio
    async def test_simple_plan(self, orchestrator):
        """Test simple plan creation."""
        plan = await orchestrator._create_plan(
            "what is X",
            [],
            TaskComplexity.SIMPLE
        )

        assert len(plan.steps) == 1
        assert plan.steps[0].action == "answer"
        assert plan.status == "ready"

    @pytest.mark.asyncio
    async def test_moderate_plan(self, orchestrator):
        """Test moderate plan creation."""
        plan = await orchestrator._create_plan(
            "explain this",
            [],
            TaskComplexity.MODERATE
        )

        assert len(plan.steps) == 2
        assert plan.steps[0].action == "search"
        assert plan.steps[1].action == "answer"
        assert plan.steps[1].depends_on == [1]


class TestPlanExecution:
    """Tests for plan execution."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch('src.agents.orchestrator.LLMClient'), \
             patch('src.agents.orchestrator.ModelRouter'), \
             patch('src.agents.orchestrator.SemanticStore'), \
             patch('src.agents.orchestrator.ActionExecutor'):
            orchestrator = Orchestrator()
            orchestrator.store = MagicMock()
            orchestrator.llm = MagicMock()
            orchestrator.router = MagicMock()
            return orchestrator

    @pytest.mark.asyncio
    async def test_search_step_execution(self, orchestrator):
        """Test search step execution."""
        orchestrator.store.search.return_value = [{"content": "result"}]

        step = PlanStep(
            step_id=1,
            action="search",
            description="Search",
            params={"query": "test"}
        )
        plan = ExecutionPlan(goal="test", steps=[step])

        result = await orchestrator._execute_step(step, plan)

        assert result == [{"content": "result"}]
        orchestrator.store.search.assert_called_with("test", limit=10)

    @pytest.mark.asyncio
    async def test_semantic_search_step(self, orchestrator):
        """Test semantic search step execution."""
        orchestrator.store.semantic_search.return_value = [{"content": "semantic result"}]

        step = PlanStep(
            step_id=1,
            action="semantic_search",
            description="Semantic search",
            params={"query": "meaning-based search"}
        )
        plan = ExecutionPlan(goal="test", steps=[step])

        result = await orchestrator._execute_step(step, plan)

        orchestrator.store.semantic_search.assert_called_with("meaning-based search", limit=10)

    @pytest.mark.asyncio
    async def test_plan_execution_completes_all_steps(self, orchestrator):
        """Test that plan execution completes all steps."""
        orchestrator.store.search.return_value = []
        orchestrator.llm.generate = AsyncMock(return_value={"content": "Answer"})
        orchestrator.router.route.return_value = "test-model"

        step1 = PlanStep(step_id=1, action="search", description="Search")
        step2 = PlanStep(step_id=2, action="answer", description="Answer", depends_on=[1])
        plan = ExecutionPlan(goal="test", steps=[step1, step2])

        await orchestrator._execute_plan(plan)

        assert step1.status == "completed"
        assert step2.status == "completed"
        assert plan.status == "completed"


class TestResponseGeneration:
    """Tests for response generation."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch('src.agents.orchestrator.LLMClient'), \
             patch('src.agents.orchestrator.ModelRouter'), \
             patch('src.agents.orchestrator.SemanticStore'), \
             patch('src.agents.orchestrator.ActionExecutor'):
            return Orchestrator()

    @pytest.mark.asyncio
    async def test_response_from_answer_step(self, orchestrator):
        """Test response extraction from answer step."""
        step = PlanStep(
            step_id=1,
            action="answer",
            description="Answer",
            status="completed",
            result="This is the answer"
        )
        plan = ExecutionPlan(goal="test", steps=[step])

        response = await orchestrator._generate_response(plan)

        assert response == "This is the answer"

    @pytest.mark.asyncio
    async def test_response_fallback(self, orchestrator):
        """Test response fallback when no answer step."""
        step = PlanStep(
            step_id=1,
            action="search",
            description="Search",
            status="completed",
            result=[{"content": "Search result"}]
        )
        plan = ExecutionPlan(goal="test", steps=[step])

        response = await orchestrator._generate_response(plan)

        assert "Search result" in response or "analysis" in response.lower()

    @pytest.mark.asyncio
    async def test_no_results_response(self, orchestrator):
        """Test response when no results available."""
        step = PlanStep(
            step_id=1,
            action="search",
            description="Search",
            status="failed",
            result=None
        )
        plan = ExecutionPlan(goal="test", steps=[step])

        response = await orchestrator._generate_response(plan)

        assert "wasn't able" in response.lower() or "not" in response.lower()


class TestConversationHistory:
    """Tests for conversation history management."""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with mocked dependencies."""
        with patch('src.agents.orchestrator.LLMClient'), \
             patch('src.agents.orchestrator.ModelRouter'), \
             patch('src.agents.orchestrator.SemanticStore'), \
             patch('src.agents.orchestrator.ActionExecutor'):
            return Orchestrator()

    def test_clear_history(self, orchestrator):
        """Test clearing conversation history."""
        orchestrator.conversation_history = [
            {"role": "user", "content": "test"},
            {"role": "assistant", "content": "response"}
        ]

        orchestrator.clear_history()

        assert orchestrator.conversation_history == []

    def test_get_history(self, orchestrator):
        """Test getting conversation history copy."""
        orchestrator.conversation_history = [
            {"role": "user", "content": "test"}
        ]

        history = orchestrator.get_history()

        assert history == [{"role": "user", "content": "test"}]
        # Verify it's a copy
        history.append({"role": "assistant", "content": "new"})
        assert len(orchestrator.conversation_history) == 1


class TestAvailableTools:
    """Tests for available tools configuration."""

    def test_all_tools_have_required_fields(self):
        """Test that all tools have required configuration fields."""
        for tool_name, tool_info in Orchestrator.AVAILABLE_TOOLS.items():
            assert "description" in tool_info, f"{tool_name} missing description"
            assert "params" in tool_info, f"{tool_name} missing params"
            assert "requires_approval" in tool_info, f"{tool_name} missing requires_approval"

    def test_sensitive_actions_require_approval(self):
        """Test that sensitive actions require approval."""
        sensitive_tools = ["open_file"]

        for tool_name in sensitive_tools:
            if tool_name in Orchestrator.AVAILABLE_TOOLS:
                assert Orchestrator.AVAILABLE_TOOLS[tool_name]["requires_approval"] is True

    def test_read_only_actions_no_approval(self):
        """Test that read-only actions don't require approval."""
        read_only_tools = ["search", "semantic_search", "get_entities", "answer"]

        for tool_name in read_only_tools:
            if tool_name in Orchestrator.AVAILABLE_TOOLS:
                assert Orchestrator.AVAILABLE_TOOLS[tool_name]["requires_approval"] is False
