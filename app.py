from flask import Flask, jsonify, request, send_file
import tempfile
from datetime import datetime
from functools import wraps
import os

# Import our modules
from config import (
    API_KEYS, FLASK_HOST, FLASK_PORT, FLASK_DEBUG, 
    get_logger, generate_api_key
)
from utils import (
    validate_time_format, validate_datetime_format,
    cleanup_temp_file, cleanup_temp_dir, ensure_naive_datetime
)
from video_manager import VideoAnnotationManager
from services import S3Service, SchedulerService

# Initialize Flask app
app = Flask(__name__)
logger = get_logger(__name__)

# Initialize services
video_manager = VideoAnnotationManager()
s3_service = S3Service()
scheduler_service = SchedulerService(video_manager, s3_service)

# Authentication
def validate_api_key(provided_key: str) -> bool:
    """Validate the provided API key"""
    return provided_key in API_KEYS.values()

def require_api_key(f):
    """Decorator to require API key authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from request headers
        api_key = request.headers.get('X-API-Key') or request.headers.get('Authorization')
        
        if not api_key:
            logger.warning(f"API request without key from {request.remote_addr}")
            return jsonify({'error': 'API key required'}), 401
        
        # Handle 'Bearer token' format
        if api_key.startswith('Bearer '):
            api_key = api_key[7:]  # Remove 'Bearer ' (7 characters)
        
        if not validate_api_key(api_key):
            logger.warning(f"Invalid API key attempt from {request.remote_addr}")
            return jsonify({'error': 'Invalid API key'}), 401
        
        logger.info(f"Authenticated request to {request.endpoint}")
        return f(*args, **kwargs)
    
    return decorated_function

# Public endpoints (no auth required)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint - public"""
    return jsonify({
        "status": "healthy", 
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    })

@app.route('/auth/generate-key', methods=['POST'])
def generate_new_api_key():
    """Generate a new API key - for testing purposes"""
    new_key = generate_api_key()
    return jsonify({
        "api_key": new_key,
        "note": "This is for testing only. In production, keys should be managed securely."
    })

# Protected endpoints (require authentication)

@app.route('/upload/manual', methods=['POST'])
@require_api_key
def manual_upload():
    """Manually trigger upload"""
    try:
        result = scheduler_service.routine_upload()
        return jsonify({
            "status": "success", 
            "message": "Upload completed",
            "result": result
        })
    except Exception as e:
        logger.error(f"Manual upload failed: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/schedule', methods=['GET'])
@require_api_key
def get_schedule():
    """Get current upload schedule"""
    return jsonify({
        "upload_times": scheduler_service.upload_times,
        "scheduler_running": scheduler_service.is_running
    })

@app.route('/schedule', methods=['POST'])
@require_api_key
def update_schedule():
    """Update upload schedule"""
    data = request.get_json()
    
    if 'upload_times' not in data:
        return jsonify({"status": "error", "message": "upload_times required"}), 400
    
    new_times = data['upload_times']
    
    # Validate time format
    for time_str in new_times:
        if not validate_time_format(time_str):
            return jsonify({"status": "error", "message": f"Invalid time format: {time_str}"}), 400
    
    try:
        scheduler_service.update_schedule(new_times)
        return jsonify({
            "status": "success", 
            "upload_times": scheduler_service.upload_times
        })
    except Exception as e:
        logger.error(f"Failed to update schedule: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/query/s3', methods=['GET'])
@require_api_key
def query_s3_files():
    """Query available files on S3"""
    try:
        files = s3_service.list_files()
        return jsonify({"files": files, "count": len(files)})
    except Exception as e:
        logger.error(f"Failed to query S3 files: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/query/local', methods=['GET'])
@require_api_key  # FIXED: Added authentication
def query_local_files():
    """Query available local files with IDs"""
    try:
        video_files = video_manager.get_video_files()
        file_info = []
        
        for video_file in video_files:
            info = video_manager.get_video_info(video_file)
            file_info.append(info)
        
        # Sort by datetime
        file_info.sort(key=lambda x: x['datetime'] or '', reverse=True)
        
        return jsonify({"files": file_info, "count": len(file_info)})
        
    except Exception as e:
        logger.error(f"Failed to query local files: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/local/<file_id>', methods=['GET'])
@require_api_key
def download_local_file(file_id):
    """Download specific local file by ID"""
    try:
        video_file = video_manager.get_video_by_id(file_id)
        if not video_file:
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create archive
            archive_path = video_manager.create_archive_for_video(video_file, temp_dir)
            archive_filename = os.path.basename(archive_path)
            
            # Clean up after download
            cleanup_temp_dir(temp_dir, delay=120)  # 2 minutes delay
            
            return send_file(
                archive_path,
                as_attachment=True,
                download_name=archive_filename,
                mimetype='application/gzip'
            )
        except Exception as e:
            cleanup_temp_dir(temp_dir)
            raise e
            
    except Exception as e:
        logger.error(f"Failed to download local file {file_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/s3/<s3_file_id>', methods=['GET'])
@require_api_key
def download_s3_file(s3_file_id):
    """Download specific file from S3 by ID"""
    try:
        # Find the S3 object by ID
        target_key = s3_service.find_file_by_id(s3_file_id)
        
        if not target_key:
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz')
        
        # Download from S3
        if not s3_service.download_file(target_key, temp_file.name):
            cleanup_temp_file(temp_file.name)
            return jsonify({"status": "error", "message": "Failed to download from S3"}), 500
        
        filename = os.path.basename(target_key)
        
        # Clean up temp file after download
        cleanup_temp_file(temp_file.name, delay=120)
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/gzip'
        )
        
    except Exception as e:
        logger.error(f"Failed to download S3 file {s3_file_id}: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/range', methods=['POST'])
@require_api_key
def download_range():
    """Download files within a time range"""
    data = request.get_json()
    
    if 'start_time' not in data or 'end_time' not in data:
        return jsonify({"status": "error", "message": "start_time and end_time required"}), 400
    
    try:
        start_time = validate_datetime_format(data['start_time'])
        end_time = validate_datetime_format(data['end_time'])
        
        if not start_time or not end_time:
            return jsonify({"status": "error", "message": "Invalid datetime format. Use ISO format like '2025-04-17T08:00:00'"}), 400
        
        # Ensure both datetimes are naive for comparison
        start_time = ensure_naive_datetime(start_time)
        end_time = ensure_naive_datetime(end_time)
        
        if start_time >= end_time:
            return jsonify({"status": "error", "message": "start_time must be before end_time"}), 400
        
        # Get videos in range
        videos_in_range = video_manager.get_videos_in_time_range(start_time, end_time)
        
        if not videos_in_range:
            return jsonify({"status": "error", "message": f"No videos found in time range {start_time} to {end_time}"}), 404
        
        # Create combined archive
        temp_dir = tempfile.mkdtemp()
        archive_name = f"range_{start_time.strftime('%Y%m%d_%H%M%S')}_to_{end_time.strftime('%Y%m%d_%H%M%S')}.tar.gz"
        
        try:
            archive_path = video_manager.create_range_archive(videos_in_range, archive_name)
            archive_path = os.path.join(temp_dir, archive_name)  # Ensure correct path
            
            # Move the created archive to temp_dir if it's not already there
            if not os.path.exists(archive_path):
                created_archive = video_manager.create_range_archive(videos_in_range, archive_name)
                if created_archive != archive_path:
                    import shutil
                    shutil.move(created_archive, archive_path)
            
            logger.info(f"Created range archive: {archive_path} with {len(videos_in_range)} videos")
            
            # Clean up temp dir after download
            cleanup_temp_dir(temp_dir, delay=120)
            
            return send_file(
                archive_path,
                as_attachment=True,
                download_name=archive_name,
                mimetype='application/gzip'
            )
        except Exception as e:
            cleanup_temp_dir(temp_dir)
            raise e
            
    except Exception as e:
        logger.error(f"Failed to download range: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Legacy endpoint for backward compatibility
@app.route('/query', methods=['GET'])
@require_api_key
def query_files():
    """Query both local and S3 files"""
    try:
        video_files = video_manager.get_video_files()
        local_info = [video_manager.get_video_info(f) for f in video_files]
        s3_files = s3_service.list_files()
        
        return jsonify({
            "local": {"files": local_info, "count": len(local_info)},
            "s3": {"files": s3_files, "count": len(s3_files)}
        })
        
    except Exception as e:
        logger.error(f"Failed to query files: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({"status": "error", "message": "Endpoint not found"}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({"status": "error", "message": "Internal server error"}), 500

if __name__ == '__main__':
    # Start scheduler
    scheduler_service.start_scheduler()
    
    logger.info(f"Starting Video Annotation Service on {FLASK_HOST}:{FLASK_PORT}")
    app.run(host=FLASK_HOST, port=FLASK_PORT, debug=FLASK_DEBUG)
