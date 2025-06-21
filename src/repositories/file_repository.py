"""File repository for managing file operations."""

import json
from pathlib import Path
from typing import Any, Dict, Optional, Union
from loguru import logger


class FileRepository:
    """Repository for file operations."""
    
    def __init__(self, base_path: Optional[Path] = None):
        """Initialize file repository.
        
        Args:
            base_path: Base directory for file operations
        """
        self.base_path = base_path or Path("./output")
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    async def save_content(
        self,
        content: str,
        filename: str,
        subdirectory: Optional[Union[str, Path]] = None,
        encoding: str = "utf-8"
    ) -> Path:
        """Save text content to file.
        
        Args:
            content: Content to save
            filename: Filename
            subdirectory: Optional subdirectory
            encoding: File encoding
            
        Returns:
            Path to saved file
        """
        # Determine full path
        if subdirectory:
            dir_path = self.base_path / subdirectory
        else:
            dir_path = self.base_path
        
        dir_path.mkdir(parents=True, exist_ok=True)
        
        file_path = dir_path / filename
        
        # Save content
        try:
            file_path.write_text(content, encoding=encoding)
            logger.debug(f"Saved file: {file_path}")
            return file_path
        except Exception as e:
            logger.error(f"Failed to save file {file_path}: {e}")
            raise
    
    async def save_json(
        self,
        data: Union[dict, list],
        filename: str,
        subdirectory: Optional[Union[str, Path]] = None,
        indent: int = 2
    ) -> Path:
        """Save data as JSON file.
        
        Args:
            data: Data to save
            filename: Filename
            subdirectory: Optional subdirectory
            indent: JSON indentation
            
        Returns:
            Path to saved file
        """
        content = json.dumps(data, ensure_ascii=False, indent=indent)
        return await self.save_content(content, filename, subdirectory)
    
    async def read_content(
        self,
        filename: str,
        subdirectory: Optional[Union[str, Path]] = None,
        encoding: str = "utf-8"
    ) -> str:
        """Read text content from file.
        
        Args:
            filename: Filename
            subdirectory: Optional subdirectory
            encoding: File encoding
            
        Returns:
            File content
        """
        if subdirectory:
            file_path = self.base_path / subdirectory / filename
        else:
            file_path = self.base_path / filename
        
        try:
            return file_path.read_text(encoding=encoding)
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            raise
    
    async def read_json(
        self,
        filename: str,
        subdirectory: Optional[Union[str, Path]] = None
    ) -> Union[dict, list]:
        """Read JSON data from file.
        
        Args:
            filename: Filename
            subdirectory: Optional subdirectory
            
        Returns:
            Parsed JSON data
        """
        content = await self.read_content(filename, subdirectory)
        return json.loads(content)
    
    def exists(
        self,
        filename: str,
        subdirectory: Optional[Union[str, Path]] = None
    ) -> bool:
        """Check if file exists.
        
        Args:
            filename: Filename
            subdirectory: Optional subdirectory
            
        Returns:
            True if file exists
        """
        if subdirectory:
            file_path = self.base_path / subdirectory / filename
        else:
            file_path = self.base_path / filename
        
        return file_path.exists()
    
    def list_files(
        self,
        subdirectory: Optional[Union[str, Path]] = None,
        pattern: str = "*",
        recursive: bool = False
    ) -> list[Path]:
        """List files in directory.
        
        Args:
            subdirectory: Optional subdirectory
            pattern: File pattern (glob)
            recursive: Whether to search recursively
            
        Returns:
            List of file paths
        """
        if subdirectory:
            search_path = self.base_path / subdirectory
        else:
            search_path = self.base_path
        
        if recursive:
            return list(search_path.rglob(pattern))
        else:
            return list(search_path.glob(pattern))
    
    async def delete_file(
        self,
        filename: str,
        subdirectory: Optional[Union[str, Path]] = None
    ) -> bool:
        """Delete a file.
        
        Args:
            filename: Filename
            subdirectory: Optional subdirectory
            
        Returns:
            True if file was deleted
        """
        if subdirectory:
            file_path = self.base_path / subdirectory / filename
        else:
            file_path = self.base_path / filename
        
        try:
            if file_path.exists():
                file_path.unlink()
                logger.debug(f"Deleted file: {file_path}")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to delete file {file_path}: {e}")
            raise
    
    def create_directory(
        self,
        directory: Union[str, Path],
        parents: bool = True
    ) -> Path:
        """Create a directory.
        
        Args:
            directory: Directory path
            parents: Whether to create parent directories
            
        Returns:
            Path to created directory
        """
        dir_path = self.base_path / directory
        dir_path.mkdir(parents=parents, exist_ok=True)
        return dir_path
    
    def get_file_info(
        self,
        filename: str,
        subdirectory: Optional[Union[str, Path]] = None
    ) -> Dict[str, Any]:
        """Get file information.
        
        Args:
            filename: Filename
            subdirectory: Optional subdirectory
            
        Returns:
            File information dictionary
        """
        if subdirectory:
            file_path = self.base_path / subdirectory / filename
        else:
            file_path = self.base_path / filename
        
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
        
        stats = file_path.stat()
        
        return {
            "path": str(file_path),
            "size": stats.st_size,
            "created": stats.st_ctime,
            "modified": stats.st_mtime,
            "is_file": file_path.is_file(),
            "is_dir": file_path.is_dir(),
            "extension": file_path.suffix
        }