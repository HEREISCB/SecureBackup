import os
import logging
from datetime import datetime
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager
from flask_migrate import Migrate  # Import Migrate
from werkzeug.middleware.proxy_fix import ProxyFix

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass



db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()


app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "dev-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)  


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///backup_system.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False


app.config["UPLOAD_FOLDER"] = os.path.join(os.getcwd(), "file_storage")
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  


app.config["BACKUP_TEMP_DIR"] = os.path.join(os.getcwd(), "backup_temp")
app.config["DEFAULT_BACKUP_INTERVAL"] = 60 
app.config["ALLOWED_BACKUP_INTERVALS"] = [15, 30, 60, 360, 720, 1440]  
app.config["MAX_MONITORED_FOLDERS_PER_USER"] = 10
app.config["MONITOR_ENABLED"] = True  


os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(app.config["BACKUP_TEMP_DIR"], exist_ok=True)


db.init_app(app)
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message_category = "info"

migrate = Migrate(app, db) # Initialize Migrate


with app.app_context():

    from models import User, File, FileVersion, MonitoredFolder, BackupJob, BackupLog


    # db.create_all() # Remove this line, migrations will handle it

    from routes import register_routes
    register_routes(app)
    
    logger.info("Application initialized successfully")
