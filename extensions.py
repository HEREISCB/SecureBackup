from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from flask_login import LoginManager

class Base(DeclarativeBase):
    pass

# Initialize extensions here
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()