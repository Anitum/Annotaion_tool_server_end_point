import boto3
import schedule
import time
import threading
import hashlib
import os
import tempfile  # Fixed: Added missing import
from datetime import datetime
from typing import List, Dict, Optional
from botocore.exceptions import ClientError
from config import S3_BUCKET, S3_PREFIX, UPLOAD_TIMES, get_logger
from video_manager import VideoAnnotationManager
from utils import cleanup_temp_dir, parse_datetime_from_filename  # Fixed: Added missing import

logger = get_logger(__name__)

class S3Service:
    def __init__(self, bucket_name: str = S3_BUCKET):
        self.bucket_name = bucket_name
        self.s3_client = boto3.client('s3')
        
    def upload_file(self, local_file_path: str, s3_key: str) -> bool:
        """Upload file to S3"""
        try:
            self.s3_client.upload_file(local_file_path, self.bucket_name, s3_key)
            logger.info(f"Successfully uploaded {s3_key} to S3")
            return True
        except ClientError as e:
            logger.error(f"Failed to upload {s3_key}: {e}")
            return False
    
    def download_file(self, s3_key: str, local_file_path: str) -> bool:
        """Download file from S3"""
        try:
            self.s3_client.download_file(self.bucket_name, s3_key, local_file_path)
            logger.info(f"Successfully downloaded {s3_key} from S3")
            return True
        except ClientError as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            return False
    
    def list_files(self, prefix: str = S3_PREFIX) -> List[Dict]:
        """List files in S3 bucket with prefix"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            files = []
            if 'Contents' in response:
                for obj in response['Contents']:
                    if obj['Key'].endswith('.tar.gz'):  # Only show tar.gz files
                        files.append({
                            "id": hashlib.md5(obj['Key'].encode()).hexdigest()[:12],
                            "key": obj['Key'],
                            "size": obj['Size'],
                            "size_mb": round(obj['Size'] / (1024 * 1024), 2),
                            "last_modified": obj['LastModified'].isoformat(),
                            "filename": os.path.basename(obj['Key'])
                        })
            
            return files
            
        except ClientError as e:
            logger.error(f"Failed to list S3 files: {e}")
            return []
    
    def find_file_by_id(self, file_id: str, prefix: str = S3_PREFIX) -> Optional[str]:
        """Find S3 file key by ID"""
        try:
            response = self.s3_client.list_objects_v2(
                Bucket=self.bucket_name,
                Prefix=prefix
            )
            
            if 'Contents' in response:
                for obj in response['Contents']:
                    if hashlib.md5(obj['Key'].encode()).hexdigest()[:12] == file_id:
                        return obj['Key']
            
            return None
            
        except ClientError as e:
            logger.error(f"Failed to find S3 file by ID: {e}")
            return None

class SchedulerService:
    def __init__(self, video_manager: VideoAnnotationManager, s3_service: S3Service):
        self.video_manager = video_manager
        self.s3_service = s3_service
        self.upload_times = UPLOAD_TIMES.copy()
        self.scheduler_thread = None
        self.is_running = False
        
    def routine_upload(self):
        """Perform routine upload of all videos to S3"""
        logger.info("Starting routine upload...")
        
        try:
            video_files = self.video_manager.get_video_files()
            upload_count = 0
            failed_count = 0
            
            for video_file in video_files:
                try:
                    # Create archive
                    temp_dir = tempfile.mkdtemp()  # This line was failing before
                    archive_path = self.video_manager.create_archive_for_video(video_file, temp_dir)
                    
                    # Generate S3 key
                    video_datetime = parse_datetime_from_filename(video_file)  # This was also missing import
                    if video_datetime:
                        date_str = video_datetime.strftime("%Y/%m/%d")
                        s3_key = f"{S3_PREFIX}{date_str}/{os.path.basename(archive_path)}"
                    else:
                        s3_key = f"{S3_PREFIX}unknown_date/{os.path.basename(archive_path)}"
                    
                    # Upload to S3
                    if self.s3_service.upload_file(archive_path, s3_key):
                        upload_count += 1
                        logger.info(f"Successfully uploaded {video_file}")
                    else:
                        failed_count += 1
                        logger.error(f"Failed to upload {video_file}")
                    
                    # Clean up temporary files
                    cleanup_temp_dir(temp_dir)
                    
                except Exception as e:
                    logger.error(f"Failed to process {video_file}: {e}")
                    failed_count += 1
            
            logger.info(f"Routine upload completed. Uploaded: {upload_count}, Failed: {failed_count}")
            return {"uploaded": upload_count, "failed": failed_count}
            
        except Exception as e:
            logger.error(f"Routine upload failed: {e}")
            return {"uploaded": 0, "failed": 0, "error": str(e)}
    
    def update_schedule(self, new_times: List[str]):
        """Update upload schedule"""
        # Clear existing schedule
        schedule.clear()
        
        # Update times
        self.upload_times = new_times.copy()
        
        # Reschedule
        for upload_time in self.upload_times:
            schedule.every().day.at(upload_time).do(self.routine_upload)
        
        logger.info(f"Updated schedule to: {self.upload_times}")
    
    def start_scheduler(self):
        """Start the scheduler in a background thread"""
        if self.is_running:
            logger.warning("Scheduler is already running")
            return
            
        # Schedule uploads
        for upload_time in self.upload_times:
            schedule.every().day.at(upload_time).do(self.routine_upload)
        
        def run_scheduler():
            self.is_running = True
            logger.info("Scheduler started")
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
            logger.info("Scheduler stopped")
        
        self.scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.is_running = False
        schedule.clear()
        logger.info("Scheduler stop requested")

# Global services (initialized in app.py)
s3_service = None
scheduler_service = None
