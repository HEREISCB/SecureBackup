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
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
        
    def __repr__(self):
        return f'<User {self.username}>'


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
    versions = db.relationship('FileVersion', backref='file', lazy=True, cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<File {self.original_filename}>'
        
    def get_latest_version(self):
        return FileVersion.query.filter_by(file_id=self.id).order_by(FileVersion.version_number.desc()).first()
        
    def get_path(self):
        latest_version = self.get_latest_version()
        if latest_version:
            return latest_version.get_path()
        return None


class FileVersion(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_id = db.Column(db.Integer, db.ForeignKey('file.id'), nullable=False)
    version_number = db.Column(db.Integer, nullable=False)
    filename = db.Column(db.String(255), nullable=False)  # The internal filename on disk
    size = db.Column(db.Integer, nullable=False)  # Size in bytes
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_current = db.Column(db.Boolean, default=True)
    
    def __repr__(self):
        return f'<FileVersion {self.file_id}-{self.version_number}>'
        
    def get_path(self):
        from app import app
        return os.path.join(app.config['UPLOAD_FOLDER'], self.filename)
