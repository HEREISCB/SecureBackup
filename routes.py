import os
import uuid
import shutil
from datetime import datetime
from flask import render_template, url_for, flash, redirect, request, jsonify, send_file
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from app import db
from models import User, File, FileVersion
from forms import RegistrationForm, LoginForm, UploadFileForm, RenameFileForm
from utils import get_file_extension, allowed_file, create_version_directory


def register_routes(app):
    
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
        return render_template('index.html')


    @app.route('/register', methods=['GET', 'POST'])
    def register():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        form = RegistrationForm()
        if form.validate_on_submit():
            user = User(username=form.username.data, email=form.email.data)
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            flash('Account created successfully! You can now log in.', 'success')
            return redirect(url_for('login'))
            
        return render_template('register.html', form=form)


    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if current_user.is_authenticated:
            return redirect(url_for('dashboard'))
            
        form = LoginForm()
        if form.validate_on_submit():
            user = User.query.filter_by(email=form.email.data).first()
            if user and user.check_password(form.password.data):
                login_user(user, remember=form.remember.data)
                next_page = request.args.get('next')
                flash('Login successful!', 'success')
                return redirect(next_page or url_for('dashboard'))
            else:
                flash('Login unsuccessful. Please check email and password.', 'danger')
                
        return render_template('login.html', form=form)


    @app.route('/logout')
    def logout():
        logout_user()
        flash('You have been logged out.', 'info')
        return redirect(url_for('index'))


    @app.route('/dashboard')
    @login_required
    def dashboard():
        files = File.query.filter_by(user_id=current_user.id, is_deleted=False).order_by(File.updated_at.desc()).all()
        upload_form = UploadFileForm()
        rename_form = RenameFileForm()
        return render_template('dashboard.html', files=files, upload_form=upload_form, rename_form=rename_form)


    @app.route('/upload', methods=['POST'])
    @login_required
    def upload_file():
        form = UploadFileForm()
        if form.validate_on_submit():
            uploaded_file = form.file.data
            
            if not uploaded_file or not allowed_file(uploaded_file.filename):
                flash('Invalid file type. Allowed types are: txt, pdf, doc, docx, xls, xlsx, jpg, jpeg, png, gif', 'danger')
                return redirect(url_for('dashboard'))
                
            # Secure filename and create unique filename for storage
            original_filename = secure_filename(uploaded_file.filename)
            file_extension = get_file_extension(original_filename)
            unique_filename = f"{uuid.uuid4().hex}{file_extension}"
            
            # Check if this file already exists for the user
            existing_file = File.query.filter_by(
                user_id=current_user.id,
                original_filename=original_filename,
                is_deleted=False
            ).first()
            
            # If the file already exists, create a new version
            if existing_file:
                # Get the latest version number and increment
                latest_version = FileVersion.query.filter_by(file_id=existing_file.id).order_by(FileVersion.version_number.desc()).first()
                version_number = latest_version.version_number + 1 if latest_version else 1
                
                # Update all previous versions to not be current
                for version in existing_file.versions:
                    version.is_current = False
                
                # Create new version
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                uploaded_file.save(file_path)
                
                new_version = FileVersion(
                    file_id=existing_file.id,
                    version_number=version_number,
                    filename=unique_filename,
                    size=os.path.getsize(file_path),
                    is_current=True
                )
                
                # Update file metadata
                existing_file.size = os.path.getsize(file_path)
                existing_file.updated_at = datetime.utcnow()
                
                # Add and commit changes
                db.session.add(new_version)
                db.session.commit()
                
                flash(f'New version of {original_filename} uploaded successfully!', 'success')
            
            # If the file doesn't exist, create a new file entry
            else:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                uploaded_file.save(file_path)
                
                # Create file record
                new_file = File(
                    filename=unique_filename,
                    original_filename=original_filename,
                    size=os.path.getsize(file_path),
                    content_type=uploaded_file.content_type,
                    user_id=current_user.id
                )
                
                db.session.add(new_file)
                db.session.flush()  # To get the file ID
                
                # Create first version
                new_version = FileVersion(
                    file_id=new_file.id,
                    version_number=1,
                    filename=unique_filename,
                    size=os.path.getsize(file_path),
                    is_current=True
                )
                
                db.session.add(new_version)
                db.session.commit()
                
                flash(f'File {original_filename} uploaded successfully!', 'success')
                
            return redirect(url_for('dashboard'))
            
        flash('Error uploading file.', 'danger')
        return redirect(url_for('dashboard'))


    @app.route('/download/<int:file_id>')
    @login_required
    def download_file(file_id):
        file = File.query.filter_by(id=file_id, user_id=current_user.id, is_deleted=False).first_or_404()
        latest_version = file.get_latest_version()
        
        if not latest_version:
            flash('Error: File version not found.', 'danger')
            return redirect(url_for('dashboard'))
            
        file_path = latest_version.get_path()
        
        if not os.path.exists(file_path):
            flash('Error: File not found on server.', 'danger')
            return redirect(url_for('dashboard'))
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file.original_filename
        )


    @app.route('/download-version/<int:version_id>')
    @login_required
    def download_version(version_id):
        version = FileVersion.query.filter_by(id=version_id).first_or_404()
        file = File.query.filter_by(id=version.file_id, user_id=current_user.id, is_deleted=False).first_or_404()
        
        file_path = version.get_path()
        
        if not os.path.exists(file_path):
            flash('Error: File version not found on server.', 'danger')
            return redirect(url_for('file_history', file_id=file.id))
            
        return send_file(
            file_path,
            as_attachment=True,
            download_name=file.original_filename
        )


    @app.route('/delete/<int:file_id>', methods=['POST'])
    @login_required
    def delete_file(file_id):
        file = File.query.filter_by(id=file_id, user_id=current_user.id, is_deleted=False).first_or_404()
        file.is_deleted = True
        db.session.commit()
        
        flash(f'File {file.original_filename} has been deleted.', 'success')
        return redirect(url_for('dashboard'))


    @app.route('/restore/<int:file_id>', methods=['POST'])
    @login_required
    def restore_file(file_id):
        file = File.query.filter_by(id=file_id, user_id=current_user.id, is_deleted=True).first_or_404()
        file.is_deleted = False
        db.session.commit()
        
        flash(f'File {file.original_filename} has been restored.', 'success')
        return redirect(url_for('dashboard'))


    @app.route('/restore-version/<int:version_id>', methods=['POST'])
    @login_required
    def restore_version(version_id):
        version = FileVersion.query.filter_by(id=version_id).first_or_404()
        file = File.query.filter_by(id=version.file_id, user_id=current_user.id).first_or_404()
        
        # Set all versions to not current
        for v in file.versions:
            v.is_current = False
        
        # Set the selected version to current
        version.is_current = True
        file.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        flash(f'Version {version.version_number} of {file.original_filename} has been restored.', 'success')
        return redirect(url_for('file_history', file_id=file.id))


    @app.route('/rename/<int:file_id>', methods=['POST'])
    @login_required
    def rename_file(file_id):
        form = RenameFileForm()
        if form.validate_on_submit():
            file = File.query.filter_by(id=file_id, user_id=current_user.id, is_deleted=False).first_or_404()
            
            new_filename = secure_filename(form.filename.data)
            if not new_filename:
                flash('Invalid filename.', 'danger')
                return redirect(url_for('dashboard'))
                
            # Add the original extension to the new filename if it doesn't have one
            original_extension = get_file_extension(file.original_filename)
            if not get_file_extension(new_filename) and original_extension:
                new_filename += original_extension
                
            file.original_filename = new_filename
            file.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash(f'File renamed to {new_filename} successfully!', 'success')
            
        return redirect(url_for('dashboard'))


    @app.route('/history/<int:file_id>')
    @login_required
    def file_history(file_id):
        file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        versions = FileVersion.query.filter_by(file_id=file.id).order_by(FileVersion.version_number.desc()).all()
        
        return render_template('file_history.html', file=file, versions=versions)
