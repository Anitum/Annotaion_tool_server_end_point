import hashlib
import re
from datetime import datetime
from typing import Optional
import tempfile
import threading
import shutil
import os

def generate_file_id(filename: str) -> str:
    """Generate a unique ID for a file"""
    return hashlib.md5(filename.encode()).hexdigest()[:12]

def parse_datetime_from_filename(filename: str) -> Optional[datetime]:
    """Extract datetime from filename like channel1002_20250417T084930.avi"""
    pattern = r'(\d{8}T\d{6})'
    match = re.search(pattern, filename)
    if match:
        datetime_str = match.group(1)
        try:
            # Always return naive datetime for consistency
            return datetime.strptime(datetime_str, "%Y%m%dT%H%M%S")
        except ValueError:
            return None
    return None

def validate_time_format(time_str: str) -> bool:
    """Validate time format HH:MM"""
    try:
        datetime.strptime(time_str, "%H:%M")
        return True
    except ValueError:
        return False

def validate_datetime_format(datetime_str: str) -> Optional[datetime]:
    """Validate and parse ISO datetime format"""
    try:
        dt = datetime.fromisoformat(datetime_str)
        # Convert timezone-aware datetime to naive for consistency
        if dt.tzinfo is not None:
            # Convert to UTC first, then make naive
            utc_dt = dt.utctimetuple()
            dt = datetime(*utc_dt[:6])
        return dt
    except ValueError:
        return None

def cleanup_temp_file(file_path: str, delay: int = 60):
    """Clean up temporary file after delay"""
    def cleanup():
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception:
            pass
    
    threading.Timer(delay, cleanup).start()

def cleanup_temp_dir(dir_path: str, delay: int = 60):
    """Clean up temporary directory after delay"""
    def cleanup():
        try:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path, ignore_errors=True)
        except Exception:
            pass
    
    threading.Timer(delay, cleanup).start()

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    try:
        size_bytes = os.path.getsize(file_path)
        return round(size_bytes / (1024 * 1024), 2)
    except OSError:
        return 0.0

def ensure_naive_datetime(dt: datetime) -> datetime:
    """Ensure datetime is naive (no timezone info)"""
    if dt.tzinfo is not None:
        # Convert to UTC first, then make naive
        utc_dt = dt.utctimetuple()
        return datetime(*utc_dt[:6])
    return dt
