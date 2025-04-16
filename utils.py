import os
import uuid
from app import app


def get_file_extension(filename):
    """Extract the file extension from a filename including the dot"""
    if '.' in filename:
        return '.' + filename.rsplit('.', 1)[1].lower()
    return ''


def allowed_file(filename):
    """Check if file has an allowed extension"""
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx'}
    
    if '.' not in filename:
        return False
    extension = filename.rsplit('.', 1)[1].lower()
    return extension in ALLOWED_EXTENSIONS


def create_version_directory(user_id):
    """Create a unique directory for a user's file versions"""
    user_dir = os.path.join(app.config['UPLOAD_FOLDER'], str(user_id))
    os.makedirs(user_dir, exist_ok=True)
    return user_dir


def human_readable_size(size_bytes):
    """Convert bytes to human-readable format"""
    if size_bytes == 0:
        return "0B"
        
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024
        i += 1
        
    return f"{size_bytes:.2f} {size_names[i]}"
