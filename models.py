from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.dialects.postgresql import UUID
import uuid

db = SQLAlchemy()

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
            'progress': self.get_progress()
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
    
    # Extracted content
    extracted_text = db.Column(db.Text)
    
    # Results
    grade = db.Column(db.Text)
    grade_metadata = db.Column(db.JSON)  # Store provider, model, tokens used, etc.
    
    # Foreign keys
    job_id = db.Column(db.String(36), db.ForeignKey('grading_jobs.id'), nullable=False)
    
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
            'grade': self.grade,
            'grade_metadata': self.grade_metadata,
            'job_id': self.job_id
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
