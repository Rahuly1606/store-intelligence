"""
Input Validation Utilities

Follows Single Responsibility Principle - only validates input.
"""

from pathlib import Path
from typing import Tuple, Optional
from werkzeug.datastructures import FileStorage


class ValidationError(Exception):
    """Custom validation error."""
    pass


class FileValidator:
    """Validates uploaded files."""
    
    def __init__(self, allowed_extensions: set, max_size_mb: int = 500):
        self.allowed_extensions = allowed_extensions
        self.max_size_bytes = max_size_mb * 1024 * 1024
    
    def validate(self, file: FileStorage) -> Tuple[bool, Optional[str]]:
        """
        Validate uploaded file.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not file:
            return False, "No file provided"
        
        if file.filename == '':
            return False, "No file selected"
        
        if not self._has_allowed_extension(file.filename):
            return False, f"File type not allowed. Allowed: {', '.join(self.allowed_extensions)}"
        
        # Note: file.content_length might be None, handled by Flask's MAX_CONTENT_LENGTH
        
        return True, None
    
    def _has_allowed_extension(self, filename: str) -> bool:
        """Check if filename has allowed extension."""
        return '.' in filename and \
               filename.rsplit('.', 1)[1].lower() in self.allowed_extensions


class CameraTypeValidator:
    """Validates camera type input."""
    
    VALID_TYPES = {'entry', 'mainfloor', 'billing'}
    
    @classmethod
    def validate(cls, camera_type: str) -> Tuple[bool, Optional[str]]:
        """
        Validate camera type.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not camera_type:
            return False, "Camera type is required"
        
        if camera_type.lower() not in cls.VALID_TYPES:
            return False, f"Invalid camera type. Must be one of: {', '.join(cls.VALID_TYPES)}"
        
        return True, None


class StoreIdValidator:
    """Validates store ID input."""
    
    @staticmethod
    def validate(store_id: str) -> Tuple[bool, Optional[str]]:
        """
        Validate store ID.
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not store_id:
            return False, "Store ID is required"
        
        if len(store_id) < 3:
            return False, "Store ID too short"
        
        if len(store_id) > 50:
            return False, "Store ID too long"
        
        # Basic format check (alphanumeric and underscores)
        if not store_id.replace('_', '').isalnum():
            return False, "Store ID must contain only letters, numbers, and underscores"
        
        return True, None


def validate_upload_request(file: FileStorage, camera_type: str, 
                           store_id: str, allowed_extensions: set) -> None:
    """
    Validate complete upload request.
    
    Raises:
        ValidationError: If validation fails
    """
    # Validate file
    file_validator = FileValidator(allowed_extensions)
    is_valid, error = file_validator.validate(file)
    if not is_valid:
        raise ValidationError(error)
    
    # Validate camera type
    is_valid, error = CameraTypeValidator.validate(camera_type)
    if not is_valid:
        raise ValidationError(error)
    
    # Validate store ID
    is_valid, error = StoreIdValidator.validate(store_id)
    if not is_valid:
        raise ValidationError(error)
