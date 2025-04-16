from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, FileField, SelectField, IntegerField, TextAreaField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional, NumberRange
from models import User
from app import app


class RegistrationForm(FlaskForm):
    username = StringField('Username', 
                           validators=[DataRequired(), Length(min=3, max=20)])
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                             validators=[DataRequired(), Length(min=8)])
    confirm_password = PasswordField('Confirm Password',
                                      validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')
    
    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Username already taken. Please choose a different one.')
            
    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email already registered. Please use a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email',
                        validators=[DataRequired(), Email()])
    password = PasswordField('Password', 
                             validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UploadFileForm(FlaskForm):
    file = FileField('File', validators=[DataRequired()])
    submit = SubmitField('Upload')


class RenameFileForm(FlaskForm):
    filename = StringField('New Filename', validators=[DataRequired()])
    submit = SubmitField('Rename')


class MonitoredFolderForm(FlaskForm):
    name = StringField('Folder Name', validators=[DataRequired(), Length(min=1, max=255)])
    path = StringField('Folder Path', validators=[DataRequired(), Length(min=1, max=1024)])
    is_active = BooleanField('Active', default=True)
    backup_interval = SelectField('Backup Interval', 
                                 choices=[(15, '15 minutes'), 
                                          (30, '30 minutes'), 
                                          (60, '1 hour'), 
                                          (360, '6 hours'), 
                                          (720, '12 hours'), 
                                          (1440, '24 hours')],
                                 coerce=int,
                                 default=60)
    submit = SubmitField('Add Folder')
    
    def validate_path(self, path):
        import os
        # Check if the path exists and is a directory
        if not os.path.exists(path.data):
            raise ValidationError('The specified path does not exist.')
        if not os.path.isdir(path.data):
            raise ValidationError('The specified path is not a directory.')


class ManualBackupForm(FlaskForm):
    folder_id = SelectField('Select Folder', coerce=int, validators=[DataRequired()])
    name = StringField('Backup Name', validators=[DataRequired(), Length(min=1, max=255)])
    submit = SubmitField('Start Backup')


class BackupSearchForm(FlaskForm):
    query = StringField('Search', validators=[Optional()])
    date_from = StringField('From Date', validators=[Optional()])
    date_to = StringField('To Date', validators=[Optional()])
    source_type = SelectField('Source Type', 
                             choices=[('all', 'All'), ('manual', 'Manual'), ('auto', 'Automatic')],
                             default='all')
    status = SelectField('Status', 
                        choices=[('all', 'All'), ('completed', 'Completed'), ('failed', 'Failed')],
                        default='all')
    submit = SubmitField('Search')
