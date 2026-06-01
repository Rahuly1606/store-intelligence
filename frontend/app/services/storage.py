"""
Storage Service

Handles file storage operations.
Follows Single Responsibility Principle - only manages file storage.
"""

import logging
from pathlib import Path
from typing import Tuple
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

from app.utils.formatters import FilenameFormatter


logger = logging.getLogger(__name__)


class StorageError(Exception):
    """Custom exception for storage errors."""
    pass


class StorageService:
    """
    Service for managing file storage.
    
    Handles secure file saving and retrieval.
    """
    
    def __init__(self, upload_folder: Path, allowed_extensions: set):
        """
        Initialize storage service.
        
        Args:
            upload_folder: Directory for storing uploaded files
            allowed_extensions: Set of allowed file extensions
        """
        self.upload_folder = Path(upload_folder)
        self.allowed_extensions = allowed_extensions
        
        # Ensure upload folder exists
        self.upload_folder.mkdir(parents=True, exist_ok=True)
    
    def save_file(self, file: FileStorage, add_timestamp: bool = True) -> Tuple[str, Path]:
        """
        Save uploaded file securely.
        
        Args:
            file: Uploaded file object
            add_timestamp: Whether to add timestamp to filename
            
        Returns:
            Tuple of (filename, full_path)
            
        Raises:
            StorageError: If file cannot be saved
        """
        try:
            # Secure the filename
            original_filename = secure_filename(file.filename)
            filename = FilenameFormatter.sanitize(original_filename)
            
            # Add timestamp if requested
            if add_timestamp:
                filename = FilenameFormatter.add_timestamp(filename)
            
            # Construct full path
            file_path = self.upload_folder / filename
            
            # Save file
            file.save(str(file_path))
            
            logger.info(f"File saved: {filename}")
            return filename, file_path
            
        except Exception as e:
            error_msg = f"Failed to save file: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg)
    
    def delete_file(self, filename: str) -> bool:
        """
        Delete a file from storage.
        
        Args:
            filename: Name of file to delete
            
        Returns:
            True if deleted, False if file doesn't exist
            
        Raises:
            StorageError: If deletion fails
        """
        try:
            file_path = self.upload_folder / filename
            
            if not file_path.exists():
                logger.warning(f"File not found for deletion: {filename}")
                return False
            
            file_path.unlink()
            logger.info(f"File deleted: {filename}")
            return True
            
        except Exception as e:
            error_msg = f"Failed to delete file {filename}: {str(e)}"
            logger.error(error_msg)
            raise StorageError(error_msg)
    
    def get_file_path(self, filename: str) -> Path:
        """
        Get full path for a filename.
        
        Args:
            filename: Name of file
            
        Returns:
            Full path to file
        """
        return self.upload_folder / filename
    
    def file_exists(self, filename: str) -> bool:
        """
        Check if file exists in storage.
        
        Args:
            filename: Name of file
            
        Returns:
            True if file exists, False otherwise
        """
        return self.get_file_path(filename).exists()
    
    def get_file_size(self, filename: str) -> int:
        """
        Get file size in bytes.
        
        Args:
            filename: Name of file
            
        Returns:
            File size in bytes
            
        Raises:
            StorageError: If file doesn't exist
        """
        file_path = self.get_file_path(filename)
        
        if not file_path.exists():
            raise StorageError(f"File not found: {filename}")
        
        return file_path.stat().st_size
    
    def list_files(self) -> list:
        """
        List all files in storage.
        
        Returns:
            List of filenames
        """
        return [f.name for f in self.upload_folder.iterdir() if f.is_file()]
