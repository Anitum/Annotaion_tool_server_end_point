import os
import tarfile
import tempfile
from typing import List, Dict, Optional
from datetime import datetime
from config import BASE_PATH, get_logger
from utils import (
    generate_file_id, 
    parse_datetime_from_filename,
    get_file_size_mb
)

logger = get_logger(__name__)

class VideoAnnotationManager:
    def __init__(self, base_path: str = BASE_PATH):
        self.base_path = base_path
        self.modified_labels_path = os.path.join(base_path, "modified_labels")
        self._ensure_directories()
        
    def _ensure_directories(self):
        """Ensure required directories exist"""
        os.makedirs(self.base_path, exist_ok=True)
        os.makedirs(self.modified_labels_path, exist_ok=True)
        
    def get_video_files(self) -> List[str]:
        """Get all video files in the base path"""
        if not os.path.exists(self.base_path):
            logger.warning(f"Base path does not exist: {self.base_path}")
            return []
            
        video_files = []
        try:
            for file in os.listdir(self.base_path):
                if file.lower().endswith(('.avi', '.mp4', '.mov', '.mkv')):
                    video_files.append(file)
        except OSError as e:
            logger.error(f"Error reading directory {self.base_path}: {e}")
            
        return sorted(video_files)
    
    def get_video_by_id(self, file_id: str) -> Optional[str]:
        """Get video filename by ID"""
        video_files = self.get_video_files()
        for video_file in video_files:
            if generate_file_id(video_file) == file_id:
                return video_file
        return None
    
    def get_labels_for_video(self, video_filename: str) -> List[str]:
        """Get all label files for a specific video"""
        video_name = os.path.splitext(video_filename)[0]
        label_files = []
        
        if not os.path.exists(self.modified_labels_path):
            return label_files
            
        try:
            for file in os.listdir(self.modified_labels_path):
                if file.startswith(video_name + "_") and file.endswith('.txt'):
                    label_files.append(file)
        except OSError as e:
            logger.error(f"Error reading labels directory: {e}")
        
        return sorted(label_files)
    
    def get_video_info(self, video_filename: str) -> Dict:
        """Get detailed information about a video file"""
        video_path = os.path.join(self.base_path, video_filename)
        video_datetime = parse_datetime_from_filename(video_filename)
        label_files = self.get_labels_for_video(video_filename)
        
        return {
            "id": generate_file_id(video_filename),
            "filename": video_filename,
            "datetime": video_datetime.isoformat() if video_datetime else None,
            "size_mb": get_file_size_mb(video_path),
            "label_count": len(label_files),
            "labels": label_files[:10],  # Show first 10 labels
            "exists": os.path.exists(video_path)
        }
    
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
        
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                # Add video file
                tar.add(video_path, arcname=video_filename)
                logger.info(f"Added video file to archive: {video_filename}")
                
                # Add label files from modified_labels
                label_files = self.get_labels_for_video(video_filename)
                for label_file in label_files:
                    label_path = os.path.join(self.modified_labels_path, label_file)
                    if os.path.exists(label_path):
                        tar.add(label_path, arcname=f"modified_labels/{label_file}")
                        
                logger.info(f"Created archive with {len(label_files)} label files: {archive_path}")
                
        except Exception as e:
            logger.error(f"Failed to create archive for {video_filename}: {e}")
            raise
        
        return archive_path
    
    def get_videos_in_time_range(self, start_time: datetime, end_time: datetime) -> List[str]:
        """Get video files within a specific time range"""
        video_files = self.get_video_files()
        filtered_videos = []
        
        # Ensure start_time and end_time are naive (no timezone)
        if start_time.tzinfo is not None:
            start_time = start_time.replace(tzinfo=None)
        if end_time.tzinfo is not None:
            end_time = end_time.replace(tzinfo=None)
        
        logger.info(f"Searching for videos between {start_time} and {end_time}")
        
        for video_file in video_files:
            video_datetime = parse_datetime_from_filename(video_file)
            if video_datetime and start_time <= video_datetime <= end_time:
                filtered_videos.append(video_file)
                logger.info(f"Found video in range: {video_file} ({video_datetime})")
        
        logger.info(f"Found {len(filtered_videos)} videos in time range")
        return filtered_videos
    
    def create_range_archive(self, videos: List[str], archive_name: str = None) -> str:
        """Create archive for multiple videos"""
        if not videos:
            raise ValueError("No videos provided for archive creation")
            
        if archive_name is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            archive_name = f"video_range_{timestamp}.tar.gz"
            
        temp_dir = tempfile.mkdtemp()
        archive_path = os.path.join(temp_dir, archive_name)
        
        try:
            with tarfile.open(archive_path, 'w:gz') as tar:
                for video_file in videos:
                    video_path = os.path.join(self.base_path, video_file)
                    if os.path.exists(video_path):
                        tar.add(video_path, arcname=f"videos/{video_file}")
                        
                        # Add labels from modified_labels
                        label_files = self.get_labels_for_video(video_file)
                        for label_file in label_files:
                            label_path = os.path.join(self.modified_labels_path, label_file)
                            if os.path.exists(label_path):
                                tar.add(label_path, arcname=f"modified_labels/{label_file}")
                                
            logger.info(f"Created range archive with {len(videos)} videos: {archive_path}")
            
        except Exception as e:
            logger.error(f"Failed to create range archive: {e}")
            raise
            
        return archive_path
