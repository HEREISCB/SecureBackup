import os
import shutil
import hashlib
import logging
import uuid
import time
import mimetypes
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app
from app import db
from models import File, FileVersion, MonitoredFolder, BackupJob, BackupLog

logger = logging.getLogger(__name__)

def calculate_file_hash(file_path):
    """Calculate MD5 hash of a file"""
    hash_md5 = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def get_file_mime_type(file_path):
    """Get MIME type of a file"""
    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type or "application/octet-stream"

def scan_folder(folder_id):
    """Scan a monitored folder and return all files that need to be backed up"""
    folder = MonitoredFolder.query.get(folder_id)
    if not folder:
        logger.error(f"Folder with ID {folder_id} not found")
        return []
    
    if not os.path.exists(folder.path):
        logger.error(f"Folder path '{folder.path}' does not exist")
        return []
    
    # Get all files in the folder
    file_paths = []
    for root, _, files in os.walk(folder.path):
        for file in files:
            file_path = os.path.join(root, file)
            file_paths.append(file_path)
    
    logger.debug(f"Found {len(file_paths)} files in folder {folder.name}")
    return file_paths

def should_backup_file(folder_id, file_path):
    """Check if a file should be backed up based on its modification time and existing backups"""
    folder = MonitoredFolder.query.get(folder_id)
    if not folder:
        return False
    
    # Get file modification time
    try:
        mtime = os.path.getmtime(file_path)
        mod_time = datetime.fromtimestamp(mtime)
    except (OSError, ValueError) as e:
        logger.error(f"Error getting modification time for {file_path}: {e}")
        return False
    
    # Calculate relative path within the monitored folder
    rel_path = os.path.relpath(file_path, folder.path)
    
    # Check if this file already exists in the database
    existing_file = File.query.filter_by(
        source_folder_id=folder.id,
        source_path=rel_path,
        is_deleted=False
    ).first()
    
    # If file doesn't exist in our database, it should be backed up
    if not existing_file:
        return True
    
    # If file exists, check if it has been modified since last backup
    latest_version = existing_file.get_latest_version()
    if not latest_version:
        return True
    
    # If file modification time is newer than our last backup, it should be backed up
    if mod_time > latest_version.created_at:
        return True
    
    # Check file checksum if mod time is the same
    if mod_time == latest_version.created_at and latest_version.checksum:
        current_checksum = calculate_file_hash(file_path)
        if current_checksum != latest_version.checksum:
            return True
    
    return False

def create_backup_job(user_id, name=None, is_manual=False):
    """Create a new backup job"""
    if not name:
        name = f"Backup {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    job = BackupJob(
        name=name,
        user_id=user_id,
        status="pending",
        is_manual=is_manual
    )
    
    db.session.add(job)
    db.session.commit()
    
    return job

def backup_file(file_path, folder_id, job_id=None):
    """Backup a single file"""
    folder = MonitoredFolder.query.get(folder_id)
    if not folder:
        logger.error(f"Folder with ID {folder_id} not found")
        return None
    
    if not os.path.exists(file_path):
        logger.error(f"File {file_path} does not exist")
        return None
    
    # Secure filename and create unique filename for storage
    original_filename = os.path.basename(file_path)
    safe_original_filename = secure_filename(original_filename)
    file_extension = os.path.splitext(safe_original_filename)[1].lower()
    unique_filename = f"{uuid.uuid4().hex}{file_extension}"
    
    # Calculate relative path within the monitored folder
    rel_path = os.path.relpath(file_path, folder.path)
    
    # Get file information
    try:
        file_size = os.path.getsize(file_path)
        file_hash = calculate_file_hash(file_path)
        content_type = get_file_mime_type(file_path)
    except (OSError, IOError) as e:
        logger.error(f"Error accessing file {file_path}: {e}")
        return None
    
    # Check if this file already exists in the database
    existing_file = File.query.filter_by(
        source_folder_id=folder.id,
        source_path=rel_path,
        is_deleted=False
    ).first()
    
    new_version = None
    
    # File exists in the system, add a new version
    if existing_file:
        # Get the latest version number and increment
        latest_version = FileVersion.query.filter_by(file_id=existing_file.id).order_by(FileVersion.version_number.desc()).first()
        version_number = (latest_version.version_number + 1) if latest_version else 1
        
        # Update all previous versions to not be current
        for version in existing_file.versions:
            version.is_current = False
        
        # Copy file to storage location
        storage_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        try:
            shutil.copy2(file_path, storage_path)
        except (OSError, IOError) as e:
            logger.error(f"Error copying file {file_path} to {storage_path}: {e}")
            return None
        
        # Create new version
        new_version = FileVersion(
            file_id=existing_file.id,
            version_number=version_number,
            filename=unique_filename,
            size=file_size,
            is_current=True,
            checksum=file_hash,
            change_reason="Automatic backup - file modified"
        )
        
        # Update file metadata
        existing_file.size = file_size
        existing_file.updated_at = datetime.utcnow()
        
        # Add and commit changes
        db.session.add(new_version)
        db.session.commit()
        
        logger.info(f"Created new version {version_number} for file {rel_path}")
        
        # Create backup log
        if job_id:
            log = BackupLog(
                message=f"Updated file: {rel_path} (version {version_number})",
                level="info",
                folder_id=folder.id,
                job_id=job_id,
                file_id=existing_file.id
            )
            db.session.add(log)
            db.session.commit()
        
        return existing_file
    
    # File doesn't exist in the system, create a new file entry
    else:
        # Copy file to storage location
        storage_path = os.path.join(current_app.config['UPLOAD_FOLDER'], unique_filename)
        try:
            shutil.copy2(file_path, storage_path)
        except (OSError, IOError) as e:
            logger.error(f"Error copying file {file_path} to {storage_path}: {e}")
            return None
        
        # Create file record
        new_file = File(
            filename=unique_filename,
            original_filename=safe_original_filename,
            size=file_size,
            content_type=content_type,
            user_id=folder.user_id,
            source_folder_id=folder.id,
            source_path=rel_path,
            is_auto_backup=True
        )
        
        db.session.add(new_file)
        db.session.flush()  # To get the file ID
        
        # Create first version
        new_version = FileVersion(
            file_id=new_file.id,
            version_number=1,
            filename=unique_filename,
            size=file_size,
            is_current=True,
            checksum=file_hash,
            change_reason="Automatic backup - initial version"
        )
        
        db.session.add(new_version)
        db.session.commit()
        
        logger.info(f"Created new file backup for {rel_path}")
        
        # Create backup log
        if job_id:
            log = BackupLog(
                message=f"New file: {rel_path}",
                level="info",
                folder_id=folder.id,
                job_id=job_id,
                file_id=new_file.id
            )
            db.session.add(log)
            db.session.commit()
        
        return new_file

def run_backup_job(job_id):
    """Run a complete backup job for all files in all active folders for the job owner"""
    job = BackupJob.query.get(job_id)
    if not job:
        logger.error(f"Job with ID {job_id} not found")
        return False
    
    # Update job status
    job.status = "running"
    db.session.commit()
    
    try:
        start_time = time.time()
        
        # Get all active folders for the user
        folders = MonitoredFolder.query.filter_by(
            user_id=job.user_id,
            is_active=True
        ).all()
        
        if not folders:
            log = BackupLog(
                message="No active folders found for backup",
                level="warning",
                job_id=job.id
            )
            db.session.add(log)
            
            # Update job status
            job.status = "completed"
            db.session.commit()
            
            logger.warning(f"No active folders found for backup job {job.id}")
            return True
        
        total_files = 0
        backed_up_files = 0
        
        # Process each folder
        for folder in folders:
            folder.last_scan_at = datetime.utcnow()
            db.session.commit()
            
            log = BackupLog(
                message=f"Scanning folder: {folder.name} ({folder.path})",
                level="info",
                folder_id=folder.id,
                job_id=job.id
            )
            db.session.add(log)
            db.session.commit()
            
            # Get all files in the folder
            file_paths = scan_folder(folder.id)
            total_files += len(file_paths)
            
            # Check which files need to be backed up
            for file_path in file_paths:
                if should_backup_file(folder.id, file_path):
                    result = backup_file(file_path, folder.id, job.id)
                    if result:
                        backed_up_files += 1
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Create summary log
        log = BackupLog(
            message=f"Backup completed: {backed_up_files} files backed up out of {total_files} total files in {duration:.2f} seconds",
            level="info",
            job_id=job.id
        )
        db.session.add(log)
        
        # Update job status
        job.status = "completed"
        db.session.commit()
        
        logger.info(f"Backup job {job.id} completed successfully")
        return True
        
    except Exception as e:
        logger.exception(f"Error running backup job {job.id}: {e}")
        
        # Create error log
        log = BackupLog(
            message=f"Backup failed: {str(e)}",
            level="error",
            job_id=job.id
        )
        db.session.add(log)
        
        # Update job status
        job.status = "failed"
        db.session.commit()
        
        return False