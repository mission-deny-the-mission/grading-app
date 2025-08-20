from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
import uuid

db = SQLAlchemy()

class MarkingScheme(db.Model):
    """Model for storing marking schemes."""
    __tablename__ = 'marking_schemes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Marking scheme metadata
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(10))  # docx, pdf, txt
    
    # Extracted content
    content = db.Column(db.Text)
    
    # Relationships
    jobs = db.relationship('GradingJob', backref='marking_scheme', lazy=True)
    
    def to_dict(self):
        """Convert marking scheme to dictionary."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'name': self.name,
            'description': self.description,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'content': self.content
        }

class GradingJob(db.Model):
    """Model for tracking grading jobs."""
    __tablename__ = 'grading_jobs'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Job metadata
    job_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    priority = db.Column(db.Integer, default=5)  # 1-10, higher is more important
    
    # Processing info
    total_submissions = db.Column(db.Integer, default=0)
    processed_submissions = db.Column(db.Integer, default=0)
    failed_submissions = db.Column(db.Integer, default=0)
    
    # Configuration
    provider = db.Column(db.String(50), nullable=False)  # openrouter, claude, lm_studio
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(100))
    
    # Multi-model support
    models_to_compare = db.Column(db.JSON)  # List of models to use for comparison
    
    # Marking scheme reference
    marking_scheme_id = db.Column(db.String(36), db.ForeignKey('marking_schemes.id'), nullable=True)
    
    # Foreign keys
    batch_id = db.Column(db.String(36), db.ForeignKey('job_batches.id'), nullable=True)
    
    # Relationships
    submissions = db.relationship('Submission', backref='job', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert job to dictionary."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'job_name': self.job_name,
            'description': self.description,
            'status': self.status,
            'priority': self.priority,
            'total_submissions': self.total_submissions,
            'processed_submissions': self.processed_submissions,
            'failed_submissions': self.failed_submissions,
            'provider': self.provider,
            'prompt': self.prompt,
            'model': self.model,
            'models_to_compare': self.models_to_compare,
            'marking_scheme_id': self.marking_scheme_id,
            'marking_scheme': self.marking_scheme.to_dict() if self.marking_scheme else None,
            'progress': self.get_progress(),
            'can_retry': self.can_retry_failed_submissions()
        }
    
    def get_progress(self):
        """Calculate job progress percentage."""
        if self.total_submissions == 0:
            return 0
        return round((self.processed_submissions + self.failed_submissions) / self.total_submissions * 100, 2)
    
    def update_progress(self):
        """Update job progress based on submissions."""
        # Update total_submissions to match actual submission count
        actual_total = len(self.submissions)
        if self.total_submissions != actual_total:
            self.total_submissions = actual_total
        
        self.processed_submissions = sum(1 for s in self.submissions if s.status == 'completed')
        self.failed_submissions = sum(1 for s in self.submissions if s.status == 'failed')
        
        if self.processed_submissions + self.failed_submissions >= self.total_submissions:
            if self.failed_submissions == 0:
                self.status = 'completed'
            elif self.processed_submissions == 0:
                self.status = 'failed'
            else:
                self.status = 'completed_with_errors'
        
        db.session.commit()
    
    def can_retry_failed_submissions(self, max_retries=3):
        """Check if any failed submissions can be retried."""
        return any(submission.can_retry(max_retries) for submission in self.submissions)
    
    @property
    def can_retry(self):
        """Property to check if job can retry failed submissions."""
        return self.can_retry_failed_submissions()
    
    def retry_failed_submissions(self, max_retries=3):
        """Retry all failed submissions that can be retried."""
        retried_count = 0
        for submission in self.submissions:
            if submission.retry(max_retries):
                retried_count += 1
        
        if retried_count > 0:
            self.status = 'pending'
            db.session.commit()
        
        return retried_count

class GradeResult(db.Model):
    """Model for storing individual grade results from different models."""
    __tablename__ = 'grade_results'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Grade information
    grade = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # openrouter, claude, lm_studio
    model = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default='completed')  # completed, failed
    error_message = db.Column(db.Text)
    
    # Metadata
    grade_metadata = db.Column(db.JSON)  # Store usage, tokens, etc.
    
    # Foreign keys
    submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'), nullable=False)
    
    def to_dict(self):
        """Convert grade result to dictionary."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'grade': self.grade,
            'provider': self.provider,
            'model': self.model,
            'status': self.status,
            'error_message': self.error_message,
            'grade_metadata': self.grade_metadata,
            'submission_id': self.submission_id
        }

class Submission(db.Model):
    """Model for individual document submissions."""
    __tablename__ = 'submissions'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(10))  # docx, pdf
    
    # Processing status
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed, failed
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)  # Number of retry attempts
    
    # Extracted content
    extracted_text = db.Column(db.Text)
    
    # Legacy fields (for backward compatibility)
    grade = db.Column(db.Text)
    grade_metadata = db.Column(db.JSON)  # Store provider, model, tokens used, etc.
    
    # Foreign keys
    job_id = db.Column(db.String(36), db.ForeignKey('grading_jobs.id'), nullable=False)
    
    # Relationships
    grade_results = db.relationship('GradeResult', backref='submission', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        """Convert submission to dictionary."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'status': self.status,
            'error_message': self.error_message,
            'grade': self.grade,  # Legacy field
            'grade_metadata': self.grade_metadata,  # Legacy field
            'grade_results': [gr.to_dict() for gr in self.grade_results],
            'job_id': self.job_id,
            'retry_count': self.retry_count,
            'can_retry': self.can_retry()
        }
    
    def set_status(self, status, error_message=None):
        """Update submission status."""
        self.status = status
        if error_message:
            self.error_message = error_message
        self.updated_at = datetime.utcnow()
        db.session.commit()
        
        # Update job progress
        if self.job:
            self.job.update_progress()
    
    def can_retry(self, max_retries=3):
        """Check if submission can be retried."""
        return self.status == 'failed' and self.retry_count < max_retries
    
    def retry(self, max_retries=3):
        """Retry a failed submission."""
        if not self.can_retry(max_retries):
            return False
        
        self.status = 'pending'
        self.error_message = None
        self.retry_count += 1
        self.updated_at = datetime.utcnow()
        
        # Clear previous grade results for retry
        for grade_result in self.grade_results:
            db.session.delete(grade_result)
        
        db.session.commit()
        
        # Update job status if it was failed
        if self.job and self.job.status == 'failed':
            self.job.status = 'pending'
            db.session.commit()
        
        return True
    
    def add_grade_result(self, grade, provider, model, status='completed', error_message=None, metadata=None):
        """Add a new grade result to this submission."""
        grade_result = GradeResult(
            grade=grade,
            provider=provider,
            model=model,
            status=status,
            error_message=error_message,
            grade_metadata=metadata
        )
        self.grade_results.append(grade_result)
        db.session.commit()
        return grade_result

class JobBatch(db.Model):
    """Model for managing batch uploads."""
    __tablename__ = 'job_batches'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Batch metadata
    batch_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(50), default='pending')  # pending, processing, completed
    
    # Configuration
    provider = db.Column(db.String(50), nullable=False)
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(100))
    
    # Relationships
    jobs = db.relationship('GradingJob', backref='batch', lazy=True, foreign_keys='GradingJob.batch_id')
    
    def to_dict(self):
        """Convert batch to dictionary."""
        return {
            'id': self.id,
            'created_at': self.created_at.isoformat(),
            'batch_name': self.batch_name,
            'description': self.description,
            'status': self.status,
            'provider': self.provider,
            'prompt': self.prompt,
            'model': self.model,
            'total_jobs': len(self.jobs),
            'completed_jobs': sum(1 for job in self.jobs if job.status == 'completed'),
            'failed_jobs': sum(1 for job in self.jobs if job.status in ['failed', 'completed_with_errors'])
        }
