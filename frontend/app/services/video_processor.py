"""
Video Processor Service

Handles video processing pipeline execution.
Follows Single Responsibility Principle - only manages video processing.
"""

import logging
import subprocess
import sys
from pathlib import Path
from typing import Optional

from app.models.video import Video
from app.services.api_client import APIClient


logger = logging.getLogger(__name__)


class VideoProcessorError(Exception):
    """Custom exception for video processing errors."""
    pass


class VideoProcessorService:
    """
    Service for processing videos through detection pipeline.
    
    Executes the detection pipeline and monitors progress.
    """
    
    def __init__(self, pipeline_script: str, pipeline_config: str, api_client: APIClient):
        """
        Initialize video processor.
        
        Args:
            pipeline_script: Path to detection pipeline script
            pipeline_config: Path to pipeline configuration
            api_client: API client for backend communication
        """
        self.pipeline_script = Path(pipeline_script)
        self.pipeline_config = Path(pipeline_config)
        self.api_client = api_client
        self.backend_root = self.pipeline_script.parent.parent  # Backend directory
        
        # Validate pipeline script exists
        if not self.pipeline_script.exists():
            raise VideoProcessorError(f"Pipeline script not found: {pipeline_script}")
    
    def process_video(self, video: Video) -> Video:
        """
        Process video through detection pipeline.
        
        Args:
            video: Video domain model
            
        Returns:
            Updated Video model with processing status
            
        Raises:
            VideoProcessorError: If processing fails
        """
        logger.info(f"Starting video processing: {video.filename}")
        
        # Mark as processing
        video = video.mark_processing()
        
        try:
            # Build command
            command = self._build_command(video)
            
            # Execute pipeline
            self._execute_pipeline(command)
            
            # Mark as completed
            video = video.mark_completed()
            logger.info(f"Video processing completed: {video.filename}")
            
            return video
            
        except Exception as e:
            error_msg = f"Video processing failed: {str(e)}"
            logger.error(error_msg)
            video = video.mark_failed(error_msg)
            return video
    
    def _build_command(self, video: Video) -> list:
        """
        Build pipeline execution command.
        
        Args:
            video: Video domain model
            
        Returns:
            Command as list of strings
        """
        # Get Python executable (use same as current process)
        python_exe = sys.executable
        
        command = [
            python_exe,
            '-m', 'pipeline.detect',
            '--video', str(video.file_path),
            '--camera', video.camera_id,
            '--store', video.store_id,
            '--config', str(self.pipeline_config)
        ]
        
        return command
    
    def _execute_pipeline(self, command: list) -> None:
        """
        Execute pipeline command.
        
        Args:
            command: Command to execute
            
        Raises:
            VideoProcessorError: If execution fails
        """
        try:
            logger.debug(f"Executing command: {' '.join(command)}")
            logger.debug(f"Working directory: {self.backend_root}")
            
            # Execute with output capture from Backend directory
            result = subprocess.run(
                command,
                capture_output=True,
                text=True,
                check=True,
                timeout=3600,  # 1 hour timeout
                cwd=str(self.backend_root)  # Run from Backend directory
            )
            
            # Log output
            if result.stdout:
                logger.debug(f"Pipeline stdout: {result.stdout}")
            if result.stderr:
                logger.debug(f"Pipeline stderr: {result.stderr}")
                
        except subprocess.TimeoutExpired:
            raise VideoProcessorError("Pipeline execution timeout (1 hour)")
            
        except subprocess.CalledProcessError as e:
            error_msg = f"Pipeline failed with exit code {e.returncode}"
            if e.stderr:
                error_msg += f": {e.stderr}"
            raise VideoProcessorError(error_msg)
            
        except Exception as e:
            raise VideoProcessorError(f"Pipeline execution error: {str(e)}")
    
    def process_video_async(self, video: Video) -> subprocess.Popen:
        """
        Process video asynchronously (non-blocking).
        
        Args:
            video: Video domain model
            
        Returns:
            Subprocess handle
            
        Raises:
            VideoProcessorError: If process cannot be started
        """
        try:
            command = self._build_command(video)
            
            logger.info(f"Starting async video processing: {video.filename}")
            
            # Start process without waiting from Backend directory
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.backend_root)
            )
            
            return process
            
        except Exception as e:
            raise VideoProcessorError(f"Failed to start async processing: {str(e)}")
    
    def check_backend_availability(self) -> bool:
        """
        Check if backend API is available.
        
        Returns:
            True if backend is available, False otherwise
        """
        return self.api_client.is_available()
