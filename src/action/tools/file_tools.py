"""
File system tools for automated file operations.
"""
from pathlib import Path
from typing import Optional, List
import shutil
import logging

logger = logging.getLogger(__name__)


class FileTools:
    """
    Safe file system operations with built-in guardrails.
    """
    
    def __init__(self, allowed_dirs: Optional[List[Path]] = None):
        """
        Initialize FileTools with allowed directories.
        
        Args:
            allowed_dirs: List of directories where operations are permitted.
                         Defaults to user's home directory.
        """
        if allowed_dirs is None:
            home = Path.home()
            self.allowed_dirs = [
                home / "Documents",
                home / "Desktop",
                home / "Downloads",
            ]
        else:
            self.allowed_dirs = [Path(d) for d in allowed_dirs]
    
    def _is_path_allowed(self, path: Path) -> bool:
        """Check if the path is within allowed directories."""
        path = path.resolve()
        for allowed in self.allowed_dirs:
            allowed_resolved = allowed.resolve()
            if path == allowed_resolved or allowed_resolved in path.parents:
                return True
        return False
    
    def _validate_path(self, path: Path) -> Path:
        """Validate and resolve path, raising if not allowed."""
        path = Path(path).resolve()
        if not self._is_path_allowed(path):
            raise PermissionError(f"Path not in allowed directories: {path}")
        return path

    def create_file(self, path: str, content: str = "") -> dict:
        """
        Create a new file with optional content.
        
        Args:
            path: Path to the file to create.
            content: Optional content to write.
            
        Returns:
            Dict with status and path.
        """
        file_path = self._validate_path(Path(path))
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content)
        logger.info(f"Created file: {file_path}")
        return {"status": "success", "path": str(file_path)}

    def move_file(self, source: str, destination: str) -> dict:
        """
        Move a file to a new location.
        
        Args:
            source: Source file path.
            destination: Destination path.
            
        Returns:
            Dict with status and new path.
        """
        src = self._validate_path(Path(source))
        dst = self._validate_path(Path(destination))
        
        if not src.exists():
            raise FileNotFoundError(f"Source file not found: {src}")
        
        shutil.move(str(src), str(dst))
        logger.info(f"Moved file: {src} -> {dst}")
        return {"status": "success", "source": str(src), "destination": str(dst)}

    def rename_file(self, path: str, new_name: str) -> dict:
        """
        Rename a file.
        
        Args:
            path: Path to the file.
            new_name: New filename (not full path).
            
        Returns:
            Dict with status and new path.
        """
        file_path = self._validate_path(Path(path))
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        new_path = file_path.parent / new_name
        self._validate_path(new_path)
        
        file_path.rename(new_path)
        logger.info(f"Renamed file: {file_path} -> {new_path}")
        return {"status": "success", "old_path": str(file_path), "new_path": str(new_path)}

    def delete_file(self, path: str) -> dict:
        """
        Delete a file (moves to trash conceptually, but actually deletes).
        
        Args:
            path: Path to the file to delete.
            
        Returns:
            Dict with status.
        """
        file_path = self._validate_path(Path(path))
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        if file_path.is_dir():
            shutil.rmtree(file_path)
        else:
            file_path.unlink()
        
        logger.info(f"Deleted: {file_path}")
        return {"status": "success", "deleted_path": str(file_path)}

    def list_directory(self, path: str) -> dict:
        """
        List contents of a directory.
        
        Args:
            path: Path to the directory.
            
        Returns:
            Dict with list of files and directories.
        """
        dir_path = self._validate_path(Path(path))
        
        if not dir_path.is_dir():
            raise NotADirectoryError(f"Not a directory: {dir_path}")
        
        items = []
        for item in dir_path.iterdir():
            items.append({
                "name": item.name,
                "type": "directory" if item.is_dir() else "file",
                "size": item.stat().st_size if item.is_file() else None,
            })
        
        return {"status": "success", "path": str(dir_path), "items": items}

    def read_file(self, path: str) -> dict:
        """
        Read content of a file.
        
        Args:
            path: Path to the file.
            
        Returns:
            Dict with file content.
        """
        file_path = self._validate_path(Path(path))
        
        if not file_path.is_file():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        content = file_path.read_text()
        return {"status": "success", "path": str(file_path), "content": content}
