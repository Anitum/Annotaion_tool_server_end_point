from flask import Flask, jsonify, request, send_file
import os
import tarfile
import boto3
from datetime import datetime, timedelta
import schedule
import time
import threading
import re
from typing import List, Dict, Tuple
import tempfile
import shutil
import logging
from botocore.exceptions import ClientError
import hashlib

app = Flask(__name__)

# Configuration
BASE_PATH = "/home/ubuntu/runs/detect/predict5"  # Change this to your predict folder
S3_BUCKET = "a2bvideos"
S3_PREFIX = "annotation/"
UPLOAD_TIMES = ["10:00", "12:00", "13:00", "17:00", "20:00"]  # Default upload times

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize S3 client
s3_client = boto3.client('s3')

class VideoAnnotationManager:
    def __init__(self, base_path: str):
        self.base_path = base_path
        self.modified_labels_path = os.path.join(base_path, "modified_labels")
        
    def generate_file_id(self, video_filename: str) -> str:
        """Generate a unique ID for a video file"""
        return hashlib.md5(video_filename.encode()).hexdigest()[:12]
        
    def parse_datetime_from_filename(self, filename: str) -> datetime:
        """Extract datetime from filename like channel1002_20250417T084930.avi"""
        pattern = r'(\d{8}T\d{6})'
        match = re.search(pattern, filename)
        if match:
            datetime_str = match.group(1)
            return datetime.strptime(datetime_str, "%Y%m%dT%H%M%S")
        return None
    
    def get_video_files(self) -> List[str]:
        """Get all video files in the base path"""
        video_files = []
        for file in os.listdir(self.base_path):
            if file.endswith('.avi'):
                video_files.append(file)
        return video_files
    
    def get_video_by_id(self, file_id: str) -> str:
        """Get video filename by ID"""
        video_files = self.get_video_files()
        for video_file in video_files:
            if self.generate_file_id(video_file) == file_id:
                return video_file
        return None
    
    def get_labels_for_video(self, video_filename: str) -> List[str]:
        """Get all label files for a specific video"""
        video_name = os.path.splitext(video_filename)[0]
        label_files = []
        
        if os.path.exists(self.modified_labels_path):
            for file in os.listdir(self.modified_labels_path):
                if file.startswith(video_name + "_") and file.endswith('.txt'):
                    label_files.append(file)
        
        return sorted(label_files)
    
    def create_archive_for_video(self, video_filename: str, temp_dir: str = None) -> str:
        """Create tar.gz archive for video and its labels"""
        video_name = os.path.splitext(video_filename)[0]
        video_path = os.path.join(self.base_path, video_filename)
        
        if not os.path.exists(video_path):
            raise FileNotFoundError(f"Video file not found: {video_filename}")
        
        # Create temporary directory if not provided
        if temp_dir is None:
            temp_dir = tempfile.mkdtemp()
            
        archive_path = os.path.join(temp_dir, f"{video_name}.tar.gz")
        
        with tarfile.open(archive_path, 'w:gz') as tar:
            # Add video file
            tar.add(video_path, arcname=video_filename)
            
            # Add label files from modified_labels
            label_files = self.get_labels_for_video(video_filename)
            for label_file in label_files:
                label_path = os.path.join(self.modified_labels_path, label_file)
                if os.path.exists(label_path):
                    tar.add(label_path, arcname=f"modified_labels/{label_file}")
        
        return archive_path
    
    def upload_to_s3(self, local_file_path: str, s3_key: str) -> bool:
        """Upload file to S3"""
        try:
            s3_client.upload_file(local_file_path, S3_BUCKET, s3_key)
            logger.info(f"Successfully uploaded {s3_key} to S3")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload {s3_key}: {e}")
            return False
    
    def get_videos_in_time_range(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Get video files within a specific time range"""
        video_files = self.get_video_files()
        filtered_videos = []
        
        for video_file in video_files:
            video_datetime = self.parse_datetime_from_filename(video_file)
            if video_datetime and start_time <= video_datetime <= end_time:
                filtered_videos.append(video_file)
        
        return filtered_videos

# Initialize manager
manager = VideoAnnotationManager(BASE_PATH)

def routine_upload():
    """Perform routine upload of all videos to S3"""
    logger.info("Starting routine upload...")
    
    try:
        video_files = manager.get_video_files()
        upload_count = 0
        
        for video_file in video_files:
            try:
                # Create archive
                temp_dir = tempfile.mkdtemp()
                archive_path = manager.create_archive_for_video(video_file, temp_dir)
                
                # Generate S3 key
                video_datetime = manager.parse_datetime_from_filename(video_file)
                if video_datetime:
                    date_str = video_datetime.strftime("%Y/%m/%d")
                    s3_key = f"{S3_PREFIX}{date_str}/{os.path.basename(archive_path)}"
                else:
                    s3_key = f"{S3_PREFIX}unknown_date/{os.path.basename(archive_path)}"
                
                # Upload to S3
                if manager.upload_to_s3(archive_path, s3_key):
                    upload_count += 1
                
                # Clean up temporary files
                shutil.rmtree(temp_dir)
                
            except Exception as e:
                logger.error(f"Failed to process {video_file}: {e}")
        
        logger.info(f"Routine upload completed. Uploaded {upload_count} files.")
        
    except Exception as e:
        logger.error(f"Routine upload failed: {e}")

def schedule_uploads():
    """Schedule routine uploads"""
    for upload_time in UPLOAD_TIMES:
        schedule.every().day.at(upload_time).do(routine_upload)
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

# Start scheduler in background thread
scheduler_thread = threading.Thread(target=schedule_uploads, daemon=True)
scheduler_thread.start()

# API Endpoints

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})

@app.route('/upload', methods=['POST'])
def manual_upload():
    """Manually trigger upload"""
    try:
        routine_upload()
        return jsonify({"status": "success", "message": "Upload completed"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/schedule', methods=['GET'])
def get_schedule():
    """Get current upload schedule"""
    return jsonify({"upload_times": UPLOAD_TIMES})

@app.route('/schedule', methods=['POST'])
def update_schedule():
    """Update upload schedule"""
    global UPLOAD_TIMES
    data = request.get_json()
    
    if 'upload_times' not in data:
        return jsonify({"status": "error", "message": "upload_times required"}), 400
    
    new_times = data['upload_times']
    
    # Validate time format
    for time_str in new_times:
        try:
            datetime.strptime(time_str, "%H:%M")
        except ValueError:
            return jsonify({"status": "error", "message": f"Invalid time format: {time_str}"}), 400
    
    # Clear existing schedule
    schedule.clear()
    
    # Update times
    UPLOAD_TIMES = new_times
    
    # Reschedule
    for upload_time in UPLOAD_TIMES:
        schedule.every().day.at(upload_time).do(routine_upload)
    
    return jsonify({"status": "success", "upload_times": UPLOAD_TIMES})

@app.route('/query/s3', methods=['GET'])
def query_s3_files():
    """Query available files on S3"""
    try:
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_PREFIX
        )
        
        files = []
        if 'Contents' in response:
            for obj in response['Contents']:
                if obj['Key'].endswith('.tar.gz'):  # Only show tar.gz files
                    files.append({
                        "id": hashlib.md5(obj['Key'].encode()).hexdigest()[:12],
                        "key": obj['Key'],
                        "size": obj['Size'],
                        "last_modified": obj['LastModified'].isoformat(),
                        "filename": os.path.basename(obj['Key'])
                    })
        
        return jsonify({"files": files, "count": len(files)})
        
    except ClientError as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/query/local', methods=['GET'])
def query_local_files():
    """Query available local files with IDs"""
    try:
        video_files = manager.get_video_files()
        file_info = []
        
        for video_file in video_files:
            video_datetime = manager.parse_datetime_from_filename(video_file)
            label_files = manager.get_labels_for_video(video_file)
            file_id = manager.generate_file_id(video_file)
            
            file_info.append({
                "id": file_id,
                "video_file": video_file,
                "datetime": video_datetime.isoformat() if video_datetime else None,
                "label_count": len(label_files),
                "labels": label_files[:5]  # Show first 5 labels
            })
        
        # Sort by datetime
        file_info.sort(key=lambda x: x['datetime'] or '')
        
        return jsonify({"files": file_info, "count": len(file_info)})
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/local/<file_id>', methods=['GET'])
def download_local_file(file_id):
    """Download specific local file by ID"""
    try:
        video_file = manager.get_video_by_id(file_id)
        if not video_file:
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # Create temporary directory
        temp_dir = tempfile.mkdtemp()
        
        try:
            # Create archive
            archive_path = manager.create_archive_for_video(video_file, temp_dir)
            archive_filename = os.path.basename(archive_path)
            
            # Return file with proper filename
            return send_file(
                archive_path,
                as_attachment=True,
                download_name=archive_filename,
                mimetype='application/gzip'
            )
        finally:
            # Clean up will happen after file is sent
            threading.Timer(60, lambda: shutil.rmtree(temp_dir, ignore_errors=True)).start()
            
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/s3/<s3_file_id>', methods=['GET'])
def download_s3_file(s3_file_id):
    """Download specific file from S3 by ID"""
    try:
        # Find the S3 object by ID
        response = s3_client.list_objects_v2(
            Bucket=S3_BUCKET,
            Prefix=S3_PREFIX
        )
        
        target_key = None
        if 'Contents' in response:
            for obj in response['Contents']:
                if hashlib.md5(obj['Key'].encode()).hexdigest()[:12] == s3_file_id:
                    target_key = obj['Key']
                    break
        
        if not target_key:
            return jsonify({"status": "error", "message": "File not found"}), 404
        
        # Create temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.tar.gz')
        
        # Download from S3
        s3_client.download_file(S3_BUCKET, target_key, temp_file.name)
        
        filename = os.path.basename(target_key)
        
        # Clean up temp file after download
        threading.Timer(60, lambda: os.unlink(temp_file.name)).start()
        
        return send_file(
            temp_file.name,
            as_attachment=True,
            download_name=filename,
            mimetype='application/gzip'
        )
        
    except ClientError as e:
        return jsonify({"status": "error", "message": "File not found"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/download/range', methods=['POST'])
def download_range():
    """Download files within a time range"""
    data = request.get_json()
    
    if 'start_time' not in data or 'end_time' not in data:
        return jsonify({"status": "error", "message": "start_time and end_time required"}), 400
    
    try:
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        
        if start_time >= end_time:
            return jsonify({"status": "error", "message": "start_time must be before end_time"}), 400
        
        # Get videos in range
        videos_in_range = manager.get_videos_in_time_range(start_time, end_time)
        
        if not videos_in_range:
            return jsonify({"status": "error", "message": "No videos found in time range"}), 404
        
        # Create combined archive
        temp_dir = tempfile.mkdtemp()
        archive_name = f"range_{start_time.strftime('%Y%m%d_%H%M%S')}_to_{end_time.strftime('%Y%m%d_%H%M%S')}.tar.gz"
        archive_path = os.path.join(temp_dir, archive_name)
        
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                for video_file in videos_in_range:
                    video_path = os.path.join(manager.base_path, video_file)
                    if os.path.exists(video_path):
                        tar.add(video_path, arcname=f"videos/{video_file}")
                        
                        # Add labels from modified_labels
                        label_files = manager.get_labels_for_video(video_file)
                        for label_file in label_files:
                            label_path = os.path.join(manager.modified_labels_path, label_file)
                            if os.path.exists(label_path):
                                tar.add(label_path, arcname=f"modified_labels/{label_file}")
            
            # Clean up temp dir after download
            threading.Timer(60, lambda: shutil.rmtree(temp_dir, ignore_errors=True)).start()
            
            return send_file(
                archive_path,
                as_attachment=True,
                download_name=archive_name,
                mimetype='application/gzip'
            )
        except Exception as e:
            shutil.rmtree(temp_dir, ignore_errors=True)
            raise e
            
    except ValueError as e:
        return jsonify({"status": "error", "message": "Invalid datetime format. Use ISO format like '2025-04-17T08:00:00'"}), 400
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# Legacy endpoint for backward compatibility
@app.route('/query', methods=['GET'])
def query_files():
    """Query both local and S3 files"""
    try:
        local_response = query_local_files()
        s3_response = query_s3_files()
        
        local_data = local_response.get_json()
        s3_data = s3_response.get_json()
        
        return jsonify({
            "local": local_data,
            "s3": s3_data
        })
        
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
