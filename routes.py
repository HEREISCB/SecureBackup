import os
import uuid
import shutil
from datetime import datetime
from flask import render_template, url_for, flash, redirect, request, jsonify, send_file
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.utils import secure_filename
from app import db
from models import User, File, FileVersion, MonitoredFolder, BackupJob, BackupLog
from forms import RegistrationForm, LoginForm, UploadFileForm, RenameFileForm, MonitoredFolderForm, ManualBackupForm, BackupSearchForm
from utils import get_file_extension, allowed_file, create_version_directory, human_readable_size
from backup_utils import scan_folder, create_backup_job, run_backup_job
from scheduler import scheduler


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
        # Get stats for dashboard
        total_files = File.query.filter_by(user_id=current_user.id, is_deleted=False).count()
        active_folders = MonitoredFolder.query.filter_by(user_id=current_user.id, is_active=True).count()
        total_versions = FileVersion.query.join(File).filter(File.user_id == current_user.id, File.is_deleted == False).count()
        
        # Calculate total storage used
        storage_query = db.session.query(db.func.sum(File.size)).filter(
            File.user_id == current_user.id,
            File.is_deleted == False
        ).scalar()
        total_storage = storage_query or 0
        
        # Get recent files
        recent_files = File.query.filter_by(
            user_id=current_user.id, 
            is_deleted=False
        ).order_by(File.updated_at.desc()).limit(5).all()
        
        # Get recent backup jobs
        recent_jobs = BackupJob.query.filter_by(
            user_id=current_user.id
        ).order_by(BackupJob.created_at.desc()).limit(5).all()
        
        upload_form = UploadFileForm()
        rename_form = RenameFileForm()
        
        return render_template(
            'dashboard.html',
            files=recent_files,
            jobs=recent_jobs,
            upload_form=upload_form,
            rename_form=rename_form,
            stats={
                'total_files': total_files,
                'active_folders': active_folders,
                'total_versions': total_versions,
                'total_storage': human_readable_size(total_storage)
            }
        )


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
                
                # Calculate file hash for integrity verification
                from backup_utils import calculate_file_hash
                file_hash = calculate_file_hash(file_path)
                
                new_version = FileVersion(
                    file_id=existing_file.id,
                    version_number=version_number,
                    filename=unique_filename,
                    size=os.path.getsize(file_path),
                    is_current=True,
                    checksum=file_hash,
                    change_reason="Manual upload"
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
                
                # Calculate file hash for integrity verification
                from backup_utils import calculate_file_hash
                file_hash = calculate_file_hash(file_path)
                
                # Create file record
                new_file = File(
                    filename=unique_filename,
                    original_filename=original_filename,
                    size=os.path.getsize(file_path),
                    content_type=uploaded_file.content_type,
                    user_id=current_user.id,
                    is_auto_backup=False
                )
                
                db.session.add(new_file)
                db.session.flush()  # To get the file ID
                
                # Create first version
                new_version = FileVersion(
                    file_id=new_file.id,
                    version_number=1,
                    filename=unique_filename,
                    size=os.path.getsize(file_path),
                    is_current=True,
                    checksum=file_hash,
                    change_reason="Initial upload"
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
        file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        
        # If it's a regular form submission, handle with redirect
        if not request.is_json:
            file.is_deleted = True
            db.session.commit()
            flash(f'File {file.original_filename} has been deleted.', 'success')
            return redirect(url_for('dashboard'))
        
        # For AJAX requests, just mark as deleted and return JSON response
        file.is_deleted = True if not file.is_deleted else False
        db.session.commit()
        
        status = "deleted" if file.is_deleted else "active"
        
        return jsonify({
            'success': True, 
            'status': status,
            'message': f'File {file.original_filename} has been marked as {status}.'
        })


    @app.route('/restore/<int:file_id>', methods=['POST'])
    @login_required
    def restore_file(file_id):
        file = File.query.filter_by(id=file_id, user_id=current_user.id).first_or_404()
        
        # If it's a regular form submission, handle with redirect
        if not request.is_json:
            file.is_deleted = False
            db.session.commit()
            flash(f'File {file.original_filename} has been restored.', 'success')
            return redirect(url_for('dashboard'))
        
        # For AJAX requests, toggle the restored status and return JSON response
        file.is_deleted = False
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'status': 'restored',
            'message': f'File {file.original_filename} has been restored.'
        })


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


    # Backup Monitoring Routes
    
    @app.route('/monitored-folders')
    @login_required
    def monitored_folders():
        folders = MonitoredFolder.query.filter_by(user_id=current_user.id).order_by(MonitoredFolder.name).all()
        form = MonitoredFolderForm()
        
        # Get folder stats
        folder_stats = {}
        for folder in folders:
            # Count files from this folder
            file_count = File.query.filter_by(
                user_id=current_user.id,
                source_folder_id=folder.id,
                is_deleted=False
            ).count()
            
            # Get last backup time
            last_backup = BackupJob.query.join(BackupLog).filter(
                BackupJob.user_id == current_user.id,
                BackupLog.folder_id == folder.id,
                BackupJob.status == 'completed'
            ).order_by(BackupJob.created_at.desc()).first()
            
            folder_stats[folder.id] = {
                'file_count': file_count,
                'last_backup': last_backup.created_at if last_backup else None
            }
        
        return render_template(
            'monitored_folders.html',
            folders=folders,
            folder_stats=folder_stats,
            form=form,
            allowed_intervals=app.config['ALLOWED_BACKUP_INTERVALS']
        )


    @app.route('/add-folder', methods=['POST'])
    @login_required
    def add_folder():
        form = MonitoredFolderForm()
        
        # Check if user has reached the maximum number of folders
        current_folder_count = MonitoredFolder.query.filter_by(user_id=current_user.id).count()
        if current_folder_count >= app.config['MAX_MONITORED_FOLDERS_PER_USER']:
            flash(f'You have reached the maximum limit of {app.config["MAX_MONITORED_FOLDERS_PER_USER"]} monitored folders.', 'danger')
            return redirect(url_for('monitored_folders'))
        
        if form.validate_on_submit():
            # Create new monitored folder
            folder = MonitoredFolder(
                name=form.name.data,
                path=form.path.data,
                is_active=form.is_active.data,
                backup_interval=form.backup_interval.data,
                user_id=current_user.id
            )
            
            db.session.add(folder)
            db.session.commit()
            
            flash(f'Folder "{form.name.data}" has been added for monitoring.', 'success')
            
            # Trigger an initial backup
            job_name = f"Initial backup of {folder.name}"
            job_id = scheduler.trigger_manual_backup(folder.id, current_user.id, job_name)
            
            if job_id:
                flash(f'Initial backup job started for "{folder.name}".', 'info')
            
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    flash(f'{getattr(form, field).label.text}: {error}', 'danger')
        
        return redirect(url_for('monitored_folders'))


    @app.route('/edit-folder/<int:folder_id>', methods=['GET', 'POST'])
    @login_required
    def edit_folder(folder_id):
        folder = MonitoredFolder.query.filter_by(id=folder_id, user_id=current_user.id).first_or_404()
        
        if request.method == 'POST':
            # Update folder properties
            folder.name = request.form.get('name', folder.name)
            folder.is_active = 'is_active' in request.form
            
            # Validate the backup interval
            try:
                interval = int(request.form.get('backup_interval', folder.backup_interval))
                if interval in app.config['ALLOWED_BACKUP_INTERVALS']:
                    folder.backup_interval = interval
            except ValueError:
                pass
            
            db.session.commit()
            flash(f'Folder "{folder.name}" has been updated.', 'success')
            return redirect(url_for('monitored_folders'))
        
        # For GET requests, render the edit form
        form = MonitoredFolderForm(obj=folder)
        return render_template('edit_folder.html', folder=folder, form=form)


    @app.route('/delete-folder/<int:folder_id>', methods=['POST'])
    @login_required
    def delete_folder(folder_id):
        folder = MonitoredFolder.query.filter_by(id=folder_id, user_id=current_user.id).first_or_404()
        
        # Check if there are files associated with this folder
        files_count = File.query.filter_by(source_folder_id=folder_id).count()
        
        if files_count > 0:
            flash(f'Cannot delete folder "{folder.name}" because it has {files_count} files associated with it. Please delete the files first.', 'danger')
        else:
            db.session.delete(folder)
            db.session.commit()
            flash(f'Folder "{folder.name}" has been deleted.', 'success')
        
        return redirect(url_for('monitored_folders'))


    @app.route('/manual-backup', methods=['GET', 'POST'])
    @login_required
    def manual_backup():
        form = ManualBackupForm()
        
        # Populate the folder choices
        folders = MonitoredFolder.query.filter_by(user_id=current_user.id, is_active=True).all()
        form.folder_id.choices = [(f.id, f.name) for f in folders]
        
        if form.validate_on_submit():
            folder_id = form.folder_id.data
            job_name = form.name.data
            
            # Trigger manual backup
            job_id = scheduler.trigger_manual_backup(folder_id, current_user.id, job_name)
            
            if job_id:
                flash('Manual backup job started. Check the backup jobs page for status.', 'success')
                return redirect(url_for('backup_jobs'))
            else:
                flash('Failed to start backup job.', 'danger')
        
        return render_template('manual_backup.html', form=form)


    @app.route('/backup-jobs')
    @login_required
    def backup_jobs():
        # Get search parameters
        search_form = BackupSearchForm(request.args)
        
        # Build query
        query = BackupJob.query.filter_by(user_id=current_user.id)
        
        # Apply filters
        if search_form.query.data:
            query = query.filter(BackupJob.name.ilike(f'%{search_form.query.data}%'))
            
        if search_form.status.data and search_form.status.data != 'all':
            query = query.filter(BackupJob.status == search_form.status.data)
            
        if search_form.source_type.data and search_form.source_type.data != 'all':
            is_manual = search_form.source_type.data == 'manual'
            query = query.filter(BackupJob.is_manual == is_manual)
        
        # Order by newest first
        jobs = query.order_by(BackupJob.created_at.desc()).all()
        
        return render_template('backup_jobs.html', jobs=jobs, form=search_form)


    @app.route('/backup-job/<int:job_id>')
    @login_required
    def backup_job_detail(job_id):
        job = BackupJob.query.filter_by(id=job_id, user_id=current_user.id).first_or_404()
        logs = BackupLog.query.filter_by(job_id=job.id).order_by(BackupLog.timestamp).all()
        
        # Get files backed up in this job
        files = File.query.join(BackupLog, BackupLog.file_id == File.id).filter(
            BackupLog.job_id == job.id,
            File.user_id == current_user.id
        ).distinct().all()
        
        return render_template('backup_job_detail.html', job=job, logs=logs, files=files)


    @app.route('/files')
    @login_required
    def files():
        # Get search parameters
        search_term = request.args.get('search', '')
        source_type = request.args.get('source_type', 'all')
        sort_by = request.args.get('sort_by', 'updated_desc')
        show_deleted = request.args.get('show_deleted', 'true') == 'true'  # Default to showing deleted files
        
        # Build query
        query = File.query.filter_by(user_id=current_user.id)
        
        # Apply filters
        if search_term:
            query = query.filter(File.original_filename.ilike(f'%{search_term}%'))
            
        if source_type != 'all':
            is_auto = source_type == 'auto'
            query = query.filter(File.is_auto_backup == is_auto)
        
        # Apply sorting
        if sort_by == 'name_asc':
            query = query.order_by(File.original_filename)
        elif sort_by == 'name_desc':
            query = query.order_by(File.original_filename.desc())
        elif sort_by == 'size_asc':
            query = query.order_by(File.size)
        elif sort_by == 'size_desc':
            query = query.order_by(File.size.desc())
        elif sort_by == 'updated_asc':
            query = query.order_by(File.updated_at)
        else:  # default: updated_desc
            query = query.order_by(File.updated_at.desc())
        
        files = query.all()
        
        return render_template(
            'files.html',
            files=files,
            search_term=search_term,
            source_type=source_type,
            sort_by=sort_by,
            show_deleted=show_deleted,
            rename_form=RenameFileForm(),
            form=UploadFileForm()
        )
