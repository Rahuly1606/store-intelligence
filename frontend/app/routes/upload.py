"""
Upload Routes

Handles video upload and processing requests.
Follows Single Responsibility Principle - only handles HTTP layer.
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app, render_template
from werkzeug.utils import secure_filename

from app.models import Video, CameraType
from app.utils import ValidationError, validate_upload_request
from app.services import StorageError, VideoProcessorError


logger = logging.getLogger(__name__)

# Create blueprint
upload_bp = Blueprint('upload', __name__)


@upload_bp.route('/')
def index():
    """Render upload page."""
    return render_template('upload.html')


@upload_bp.route('/api/upload', methods=['POST'])
def upload_video():
    """
    Handle video upload.
    
    Expected form data:
        - file: Video file
        - camera_type: Camera type (entry/mainfloor/billing)
        - store_id: Store identifier
        
    Returns:
        JSON response with upload status
    """
    try:
        # Get services from app extensions
        storage_service = current_app.extensions['storage_service']
        
        # Validate request has file
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        camera_type = request.form.get('camera_type', '').lower()
        store_id = request.form.get('store_id', current_app.config['DEFAULT_STORE_ID'])
        
        # Validate inputs
        validate_upload_request(
            file=file,
            camera_type=camera_type,
            store_id=store_id,
            allowed_extensions=current_app.config['ALLOWED_EXTENSIONS']
        )
        
        # Save file
        filename, file_path = storage_service.save_file(file, add_timestamp=True)
        
        # Create video domain model
        video = Video(
            filename=filename,
            camera_type=CameraType.from_string(camera_type),
            store_id=store_id,
            file_path=file_path,
            uploaded_at=datetime.utcnow()
        )
        
        logger.info(f"Video uploaded successfully: {filename}")
        
        return jsonify({
            'success': True,
            'message': 'Video uploaded successfully',
            'data': video.to_dict()
        }), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except StorageError as e:
        logger.error(f"Storage error: {e}")
        return jsonify({
            'success': False,
            'error': 'Failed to save file'
        }), 500
        
    except Exception as e:
        logger.exception("Unexpected error during upload")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@upload_bp.route('/api/process', methods=['POST'])
def process_video():
    """
    Process uploaded video through detection pipeline.
    
    Expected JSON body:
        - filename: Name of uploaded file
        - camera_type: Camera type
        - store_id: Store identifier
        
    Returns:
        JSON response with processing status
    """
    try:
        # Get services
        storage_service = current_app.extensions['storage_service']
        video_processor = current_app.extensions['video_processor']
        
        # Parse request
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        filename = data.get('filename')
        camera_type = data.get('camera_type', '').lower()
        store_id = data.get('store_id', current_app.config['DEFAULT_STORE_ID'])
        
        # Validate
        if not filename:
            return jsonify({
                'success': False,
                'error': 'Filename is required'
            }), 400
        
        # Check file exists
        if not storage_service.file_exists(filename):
            return jsonify({
                'success': False,
                'error': 'File not found'
            }), 404
        
        # Create video model
        file_path = storage_service.get_file_path(filename)
        video = Video(
            filename=filename,
            camera_type=CameraType.from_string(camera_type),
            store_id=store_id,
            file_path=file_path,
            uploaded_at=datetime.utcnow()
        )
        
        # Process video (synchronous for now)
        logger.info(f"Starting video processing: {filename}")
        processed_video = video_processor.process_video(video)
        
        if processed_video.has_failed:
            return jsonify({
                'success': False,
                'error': processed_video.error_message
            }), 500
        
        logger.info(f"Video processed successfully: {filename}")
        
        return jsonify({
            'success': True,
            'message': 'Video processed successfully',
            'data': processed_video.to_dict()
        }), 200
        
    except VideoProcessorError as e:
        logger.error(f"Processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    except Exception as e:
        logger.exception("Unexpected error during processing")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500


@upload_bp.route('/api/upload-and-process', methods=['POST'])
def upload_and_process():
    """
    Upload and immediately process video (combined endpoint).
    
    Expected form data:
        - file: Video file
        - camera_type: Camera type
        - store_id: Store identifier
        
    Returns:
        JSON response with processing status
    """
    try:
        # Get services
        storage_service = current_app.extensions['storage_service']
        video_processor = current_app.extensions['video_processor']
        
        # Validate request
        if 'file' not in request.files:
            logger.warning(f"No file in request. Files: {list(request.files.keys())}")
            return jsonify({
                'success': False,
                'error': 'No file provided'
            }), 400
        
        file = request.files['file']
        camera_type = request.form.get('camera_type', '').lower()
        store_id = request.form.get('store_id', current_app.config['DEFAULT_STORE_ID'])
        
        logger.info(f"Upload request - file: {file.filename}, camera_type: '{camera_type}', store_id: {store_id}")
        
        # Validate inputs
        validate_upload_request(
            file=file,
            camera_type=camera_type,
            store_id=store_id,
            allowed_extensions=current_app.config['ALLOWED_EXTENSIONS']
        )
        
        # Save file
        filename, file_path = storage_service.save_file(file, add_timestamp=True)
        logger.info(f"Video uploaded: {filename}")
        
        # Create video model
        video = Video(
            filename=filename,
            camera_type=CameraType.from_string(camera_type),
            store_id=store_id,
            file_path=file_path,
            uploaded_at=datetime.utcnow()
        )
        
        # Process video
        logger.info(f"Processing video: {filename}")
        processed_video = video_processor.process_video(video)
        
        if processed_video.has_failed:
            return jsonify({
                'success': False,
                'error': processed_video.error_message,
                'data': processed_video.to_dict()
            }), 500
        
        logger.info(f"Video processed successfully: {filename}")
        
        return jsonify({
            'success': True,
            'message': 'Video uploaded and processed successfully',
            'data': processed_video.to_dict()
        }), 200
        
    except ValidationError as e:
        logger.warning(f"Validation error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
        
    except (StorageError, VideoProcessorError) as e:
        logger.error(f"Processing error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
        
    except Exception as e:
        logger.exception("Unexpected error")
        return jsonify({
            'success': False,
            'error': 'Internal server error'
        }), 500
