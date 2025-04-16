import threading
import time
import logging
import atexit
from datetime import datetime, timedelta
from flask import current_app
from app import db
from models import MonitoredFolder, BackupJob
from backup_utils import create_backup_job, run_backup_job

logger = logging.getLogger(__name__)

class BackupScheduler:
    def __init__(self, app=None):
        self.app = app
        self.stop_event = threading.Event()
        self.scheduler_thread = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        app.scheduler = self
        
        # Register an exit handler to stop the scheduler thread when the application shuts down
        atexit.register(self.shutdown)
    
    def start(self):
        """Start the backup scheduler thread"""
        if self.scheduler_thread is None or not self.scheduler_thread.is_alive():
            self.stop_event.clear()
            self.scheduler_thread = threading.Thread(target=self._scheduler_run, daemon=True)
            self.scheduler_thread.start()
            logger.info("Backup scheduler started")
    
    def shutdown(self):
        """Shutdown the backup scheduler"""
        if self.scheduler_thread and self.scheduler_thread.is_alive():
            logger.info("Shutting down backup scheduler...")
            self.stop_event.set()
            self.scheduler_thread.join(timeout=5)
            logger.info("Backup scheduler shutdown complete")
    
    def _scheduler_run(self):
        """Main scheduler loop that checks for folders needing backups"""
        with self.app.app_context():
            logger.info("Scheduler thread running")
            
            while not self.stop_event.is_set():
                try:
                    # Skip if monitoring is disabled in config
                    if not current_app.config.get("MONITOR_ENABLED", True):
                        time.sleep(60)  # Check every minute if monitoring is re-enabled
                        continue
                    
                    # Get all active folders
                    folders = MonitoredFolder.query.filter_by(is_active=True).all()
                    
                    for folder in folders:
                        # Check if folder needs to be backed up
                        if self._folder_needs_backup(folder):
                            logger.info(f"Starting scheduled backup for folder {folder.name} (ID: {folder.id})")
                            
                            # Create a new backup job
                            job_name = f"Scheduled backup of {folder.name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                            job = create_backup_job(folder.user_id, name=job_name)
                            
                            # Run the backup job in a separate thread to avoid blocking the scheduler
                            backup_thread = threading.Thread(
                                target=self._run_backup_job_wrapper,
                                args=(job.id,),
                                daemon=True
                            )
                            backup_thread.start()
                    
                    # Sleep for 1 minute before checking again
                    time.sleep(60)
                
                except Exception as e:
                    logger.exception(f"Error in scheduler loop: {e}")
                    time.sleep(60)  # Sleep and try again
    
    def _folder_needs_backup(self, folder):
        """Check if a folder needs to be backed up based on its backup interval"""
        # If folder has never been scanned, it needs a backup
        if folder.last_scan_at is None:
            return True
        
        # Calculate the next backup time based on the interval
        interval_minutes = folder.backup_interval
        next_backup_time = folder.last_scan_at + timedelta(minutes=interval_minutes)
        
        # If the next backup time is in the past, the folder needs a backup
        return datetime.utcnow() >= next_backup_time
    
    def _run_backup_job_wrapper(self, job_id):
        """Wrapper to run a backup job with app context"""
        with self.app.app_context():
            try:
                run_backup_job(job_id)
            except Exception as e:
                logger.exception(f"Error running backup job {job_id}: {e}")
    
    def trigger_manual_backup(self, folder_id, user_id, job_name=None):
        """Trigger a manual backup for a specific folder"""
        with self.app.app_context():
            try:
                # Create a default job name if none is provided
                if not job_name:
                    folder = MonitoredFolder.query.get(folder_id)
                    job_name = f"Manual backup of {folder.name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                # Create a new backup job
                job = create_backup_job(user_id, name=job_name, is_manual=True)
                
                # Run the backup job in a separate thread
                backup_thread = threading.Thread(
                    target=self._run_backup_job_wrapper,
                    args=(job.id,),
                    daemon=True
                )
                backup_thread.start()
                
                return job.id
            
            except Exception as e:
                logger.exception(f"Error triggering manual backup for folder {folder_id}: {e}")
                return None

# Create global scheduler instance
scheduler = BackupScheduler()