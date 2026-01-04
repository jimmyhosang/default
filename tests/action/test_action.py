"""Tests for action module."""
import pytest
import asyncio
from pathlib import Path
import tempfile
import shutil

from src.action.executor import ActionExecutor
from src.action.event_bus import EventBus, EventTypes, event_bus
from src.action.tools.file_tools import FileTools


class TestEventBus:
    """Tests for EventBus."""
    
    def setup_method(self):
        """Clear event bus before each test."""
        event_bus.clear()
    
    def test_subscribe_and_publish(self):
        """Test basic pub/sub."""
        received = []
        
        def handler(payload):
            received.append(payload)
        
        event_bus.subscribe("test.event", handler)
        event_bus.publish("test.event", {"data": "hello"})
        
        assert len(received) == 1
        assert received[0]["data"] == "hello"
    
    def test_unsubscribe(self):
        """Test unsubscribe removes handler."""
        received = []
        
        def handler(payload):
            received.append(payload)
        
        event_bus.subscribe("test.event", handler)
        event_bus.unsubscribe("test.event", handler)
        event_bus.publish("test.event", {"data": "hello"})
        
        assert len(received) == 0


class TestFileTools:
    """Tests for FileTools."""
    
    def setup_method(self):
        """Create temp directory for tests."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.file_tools = FileTools(allowed_dirs=[self.temp_dir])
    
    def teardown_method(self):
        """Clean up temp directory."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_create_file(self):
        """Test file creation."""
        path = self.temp_dir / "test.txt"
        result = self.file_tools.create_file(str(path), "Hello, World!")
        
        assert result["status"] == "success"
        assert path.exists()
        assert path.read_text() == "Hello, World!"
    
    def test_read_file(self):
        """Test file reading."""
        path = self.temp_dir / "read_test.txt"
        path.write_text("Test content")
        
        result = self.file_tools.read_file(str(path))
        
        assert result["status"] == "success"
        assert result["content"] == "Test content"
    
    def test_move_file(self):
        """Test file moving."""
        src = self.temp_dir / "source.txt"
        dst = self.temp_dir / "dest.txt"
        src.write_text("Move me")
        
        result = self.file_tools.move_file(str(src), str(dst))
        
        assert result["status"] == "success"
        assert not src.exists()
        assert dst.exists()
        assert dst.read_text() == "Move me"
    
    def test_delete_file(self):
        """Test file deletion."""
        path = self.temp_dir / "delete_me.txt"
        path.write_text("Delete me")
        
        result = self.file_tools.delete_file(str(path))
        
        assert result["status"] == "success"
        assert not path.exists()
    
    def test_list_directory(self):
        """Test directory listing."""
        (self.temp_dir / "file1.txt").write_text("1")
        (self.temp_dir / "file2.txt").write_text("2")
        (self.temp_dir / "subdir").mkdir()
        
        result = self.file_tools.list_directory(str(self.temp_dir))
        
        assert result["status"] == "success"
        assert len(result["items"]) == 3
    
    def test_path_not_allowed(self):
        """Test that paths outside allowed dirs are rejected."""
        with pytest.raises(PermissionError):
            self.file_tools.create_file("/tmp/not_allowed.txt", "content")


class TestActionExecutor:
    """Tests for ActionExecutor."""
    
    def setup_method(self):
        """Create executor and temp directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.executor = ActionExecutor()
        self.executor._file_tools = FileTools(allowed_dirs=[self.temp_dir])
        event_bus.clear()
    
    def teardown_method(self):
        """Clean up."""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_execute_file_action(self):
        """Test executing a file action."""
        path = self.temp_dir / "executor_test.txt"
        
        result = await self.executor.execute({
            "type": "file.create_file",
            "params": {"path": str(path), "content": "Executor test"}
        })
        
        assert result["status"] == "success"
        assert path.exists()
    
    @pytest.mark.asyncio
    async def test_action_events_emitted(self):
        """Test that events are emitted during execution."""
        events_received = []
        
        def handler(payload):
            events_received.append(payload)
        
        event_bus.subscribe(EventTypes.ACTION_STARTED, handler)
        event_bus.subscribe(EventTypes.ACTION_COMPLETED, handler)
        
        path = self.temp_dir / "event_test.txt"
        await self.executor.execute({
            "type": "file.create_file",
            "params": {"path": str(path), "content": "Event test"}
        })
        
        assert len(events_received) == 2
    
    @pytest.mark.asyncio
    async def test_invalid_action_type(self):
        """Test that invalid action types raise ValueError."""
        with pytest.raises(ValueError):
            await self.executor.execute({"type": "invalid", "params": {}})
    
    @pytest.mark.asyncio
    async def test_permission_check(self):
        """Test that permission checks work."""
        executor = ActionExecutor(permission_level="safe")
        
        with pytest.raises(PermissionError):
            await executor.execute({
                "type": "desktop.click",
                "params": {"x": 100, "y": 100}
            })
