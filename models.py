import os
from datetime import datetime
from app import db, login_manager
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    files = db.relationship('File', backref='owner', lazy=True)
    monitored_folders = db.relationship('MonitoredFolder', backref='owner', lazy=True)
    backup_jobs = db.relationship('BackupJob', backref='owner', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'


class MonitoredFolder(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    path = db.Column(db.String(1024), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_scan_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    backup_interval = db.Column(db.Integer, default=60)  # Backup interval in minutes
    backup_logs = db.relationship('BackupLog', backref='folder', lazy=True)
    
    def __repr__(self):
        return f'<MonitoredFolder {self.name}>'


class BackupJob(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    status = db.Column(db.String(50), default='pending')  # pending, running, completed, failed
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_manual = db.Column(db.Boolean, default=False)
    logs = db.relationship('BackupLog', backref='job', lazy=True)
    
    def __repr__(self):
        return f'<BackupJob {self.name}>'


class BackupLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    level = db.Column(db.String(20), default='info')  # info, warning, error
    folder_id = db.Column(db.Integer, db.ForeignKey('monitored_folder.id'))
    job_id = db.Column(db.Integer, db.ForeignKey('backup_job.id'))
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=True)
    
    def __repr__(self):
        return f'<BackupLog {self.id}>'


class File(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    size = db.Column(db.Integer, nullable=False)  # Size in bytes
    content_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_deleted = db.Column(db.Boolean, default=False)
    source_folder_id = db.Column(db.Integer, db.ForeignKey('monitored_folder.id'), nullable=True)
    source_path = db.Column(db.String(1024), nullable=True)  # Original path in monitored folder
    is_auto_backup = db.Column(db.Boolean, default=False)
    versions = db.relationship('FileVersion', backref='file', lazy=True, cascade="all, delete-orphan")
    backup_logs = db.relationship('BackupLog', backref='file', lazy=True)
    
    def __repr__(self):
        return f'<File {self.original_filename}>'
        
    def get_latest_version(self):
        return FileVersion.query.filter_by(file_id=self.id).order_by(FileVersion.version_number.desc()).first()
        
    def get_path(self):
        latest_version = self.get_latest_version()
        if latest_version:
            return latest_version.get_path()
        return None
        
    @property
    def source_type(self):
        """Return 'manual' or 'auto' based on how the file was added"""
        return 'auto' if self.is_auto_backup else 'manual'


class FileVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # The internal filename on disk
    size = db.Column(db.Integer, nullable=False)  # Size in bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_current = db.Column(db.Boolean, default=True)
    checksum = db.Column(db.String(128), nullable=True)  # For file integrity verification
    change_reason = db.Column(db.String(255), nullable=True)  # Description of what changed
    
    def __repr__(self):
        return f'<FileVersion {self.file_id}-{self.version_number}>'
        
    def get_path(self):
        from app import app
        return os.path.join(app.config['UPLOAD_FOLDER'], self.filename)
