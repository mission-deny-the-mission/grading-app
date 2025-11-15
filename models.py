import uuid
from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

# Prevent attribute expiration on commit to avoid DetachedInstanceError in tests and APIs
db = SQLAlchemy(session_options={"expire_on_commit": False})


class SavedPrompt(db.Model):
    """Model for storing saved prompts that can be reused."""

    __tablename__ = "saved_prompts"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Prompt metadata
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., 'essay', 'report', 'assignment'

    # Prompt content
    prompt_text = db.Column(db.Text, nullable=False)

    # Configuration
    # Provider is no longer saved with prompts; configure provider per-job instead.

    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)

    # Relationships
    jobs = db.relationship("GradingJob", backref="saved_prompt", lazy=True)

    def to_dict(self):
        """Convert saved prompt to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "prompt_text": self.prompt_text,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)
        db.session.commit()


class SavedMarkingScheme(db.Model):
    """Model for storing saved marking schemes that can be reused."""

    __tablename__ = "saved_marking_schemes"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Marking scheme metadata
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., 'essay', 'report', 'assignment'

    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(10))  # docx, pdf, txt

    # Extracted content
    content = db.Column(db.Text)

    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)

    # Relationships
    jobs = db.relationship("GradingJob", backref="saved_marking_scheme", lazy=True)

    def to_dict(self):
        """Convert saved marking scheme to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "content": self.content,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
        }

    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)
        db.session.commit()


class MarkingScheme(db.Model):
    """Model for storing marking schemes."""

    __tablename__ = "marking_schemes"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

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
    jobs = db.relationship("GradingJob", backref="marking_scheme", lazy=True)

    def to_dict(self):
        """Convert marking scheme to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "name": self.name,
            "description": self.description,
            "filename": self.filename,
            "original_filename": self.original_filename,
            "file_size": self.file_size,
            "file_type": self.file_type,
            "content": self.content,
        }


class GradingJob(db.Model):
    """Model for tracking grading jobs."""

    __tablename__ = "grading_jobs"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Job metadata
    job_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        db.String(50), default="pending"
    )  # pending, processing, completed, failed
    priority = db.Column(db.Integer, default=5)  # 1-10, higher is more important

    # Processing info
    total_submissions = db.Column(db.Integer, default=0)
    processed_submissions = db.Column(db.Integer, default=0)
    failed_submissions = db.Column(db.Integer, default=0)

    # Configuration
    provider = db.Column(db.String(50), nullable=False)  # openrouter, claude, lm_studio
    prompt = db.Column(db.Text, nullable=False)
    model = db.Column(db.String(100))

    # Model parameters
    temperature = db.Column(
        db.Float, default=0.3
    )  # Default temperature for all providers
    max_tokens = db.Column(
        db.Integer, default=2000
    )  # Default max tokens for all providers

    # Multi-model support
    models_to_compare = db.Column(db.JSON)  # List of models to use for comparison

    # Marking scheme reference
    marking_scheme_id = db.Column(
        db.String(36), db.ForeignKey("marking_schemes.id"), nullable=True
    )

    # Saved configurations references
    saved_prompt_id = db.Column(
        db.String(36), db.ForeignKey("saved_prompts.id"), nullable=True
    )
    saved_marking_scheme_id = db.Column(
        db.String(36), db.ForeignKey("saved_marking_schemes.id"), nullable=True
    )

    # Foreign keys
    batch_id = db.Column(db.String(36), db.ForeignKey("job_batches.id"), nullable=True)

    # Relationships
    submissions = db.relationship(
        "Submission", backref="job", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Convert job to dictionary."""
        try:
            # Try to access related objects, but handle detached instance errors
            marking_scheme_dict = None
            try:
                marking_scheme_dict = (
                    self.marking_scheme.to_dict() if self.marking_scheme else None
                )
            except Exception:
                pass

            saved_prompt_dict = None
            try:
                saved_prompt_dict = (
                    self.saved_prompt.to_dict() if self.saved_prompt else None
                )
            except Exception:
                pass

            saved_marking_scheme_dict = None
            try:
                saved_marking_scheme_dict = (
                    self.saved_marking_scheme.to_dict()
                    if self.saved_marking_scheme
                    else None
                )
            except Exception:
                pass

            progress = 0
            try:
                progress = self.get_progress()
            except Exception:
                pass

            can_retry = False
            try:
                can_retry = self.can_retry_failed_submissions()
            except Exception:
                pass

            return {
                "id": self.id,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "job_name": self.job_name,
                "description": self.description,
                "status": self.status,
                "priority": self.priority,
                "total_submissions": self.total_submissions,
                "processed_submissions": self.processed_submissions,
                "failed_submissions": self.failed_submissions,
                "provider": self.provider,
                "prompt": self.prompt,
                "model": self.model,
                "models_to_compare": self.models_to_compare,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "marking_scheme_id": self.marking_scheme_id,
                "marking_scheme": marking_scheme_dict,
                "saved_prompt_id": self.saved_prompt_id,
                "saved_prompt": saved_prompt_dict,
                "saved_marking_scheme_id": self.saved_marking_scheme_id,
                "saved_marking_scheme": saved_marking_scheme_dict,
                "progress": progress,
                "can_retry": can_retry,
            }
        except Exception as e:
            # Fallback for any other errors
            return {
                "id": getattr(self, "id", None),
                "job_name": getattr(self, "job_name", None),
                "status": getattr(self, "status", None),
                "error": f"Error serializing job: {str(e)}",
            }

    def get_progress(self):
        """Calculate job progress percentage."""
        if self.total_submissions == 0:
            return 0
        return round(
            (self.processed_submissions + self.failed_submissions)
            / self.total_submissions
            * 100,
            2,
        )

    def update_progress(self):
        """Update job progress based on submissions."""
        # Compute counts via queries to avoid stale relationship caching
        try:
            from models import \
                Submission  # local import to avoid circular issues
        except Exception:
            Submission = None

        if Submission is not None:
            actual_total = (
                db.session.query(Submission)
                .filter(Submission.job_id == self.id)
                .count()
            )
            processed_count = (
                db.session.query(Submission)
                .filter(Submission.job_id == self.id, Submission.status == "completed")
                .count()
            )
            failed_count = (
                db.session.query(Submission)
                .filter(Submission.job_id == self.id, Submission.status == "failed")
                .count()
            )
        else:
            # Fallback to relationship if import failed
            actual_total = len(self.submissions)
            processed_count = sum(
                1 for s in self.submissions if s.status == "completed"
            )
            failed_count = sum(1 for s in self.submissions if s.status == "failed")

        if self.total_submissions != actual_total:
            self.total_submissions = actual_total

        self.processed_submissions = processed_count
        self.failed_submissions = failed_count

        if (
            self.total_submissions > 0
            and self.processed_submissions + self.failed_submissions
            >= self.total_submissions
        ):
            if self.failed_submissions == 0:
                self.status = "completed"
            elif self.processed_submissions == 0:
                self.status = "failed"
            else:
                self.status = "completed_with_errors"

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
            self.status = "pending"
            db.session.commit()

        return retried_count

    def update_status(self):
        """Update job status based on submission states."""
        self.update_progress()
        # Ensure status reflects completed submissions
        if (
            self.total_submissions > 0
            and self.processed_submissions + self.failed_submissions
            >= self.total_submissions
        ):
            if self.failed_submissions == 0:
                self.status = "completed"
            elif self.processed_submissions == 0:
                self.status = "failed"
            else:
                self.status = "completed_with_errors"
            db.session.commit()


class GradeResult(db.Model):
    """Model for storing individual grade results from different models."""

    __tablename__ = "grade_results"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # Grade information
    grade = db.Column(db.Text, nullable=False)
    provider = db.Column(db.String(50), nullable=False)  # openrouter, claude, lm_studio
    model = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(50), default="completed")  # completed, failed
    error_message = db.Column(db.Text)

    # Metadata
    grade_metadata = db.Column(db.JSON)  # Store usage, tokens, etc.

    # Foreign keys
    submission_id = db.Column(
        db.String(36), db.ForeignKey("submissions.id"), nullable=False
    )

    def to_dict(self):
        """Convert grade result to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "grade": self.grade,
            "provider": self.provider,
            "model": self.model,
            "status": self.status,
            "error_message": self.error_message,
            "grade_metadata": self.grade_metadata,
            "submission_id": self.submission_id,
        }


class Submission(db.Model):
    """Model for individual document submissions."""

    __tablename__ = "submissions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # File information
    filename = db.Column(db.String(255), nullable=False)
    original_filename = db.Column(db.String(255), nullable=False)
    file_size = db.Column(db.Integer)
    file_type = db.Column(db.String(10))  # docx, pdf

    # Processing status
    status = db.Column(
        db.String(50), default="pending"
    )  # pending, processing, completed, failed
    error_message = db.Column(db.Text)
    retry_count = db.Column(db.Integer, default=0)  # Number of retry attempts
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)

    # Extracted content
    extracted_text = db.Column(db.Text)

    # Legacy fields (for backward compatibility)
    grade = db.Column(db.Text)
    grade_metadata = db.Column(db.JSON)  # Store provider, model, tokens used, etc.

    # Foreign keys
    job_id = db.Column(db.String(36), db.ForeignKey("grading_jobs.id"), nullable=False)

    # Relationships
    grade_results = db.relationship(
        "GradeResult", backref="submission", lazy=True, cascade="all, delete-orphan"
    )

    def to_dict(self):
        """Convert submission to dictionary."""
        try:
            grade_results_list = []
            try:
                grade_results_list = [gr.to_dict() for gr in self.grade_results]
            except Exception:
                pass

            can_retry_val = False
            try:
                can_retry_val = self.can_retry()
            except Exception:
                pass

            return {
                "id": self.id,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "filename": self.filename,
                "original_filename": self.original_filename,
                "file_size": self.file_size,
                "file_type": self.file_type,
                "status": self.status,
                "error_message": self.error_message,
                "grade": self.grade,  # Legacy field
                "grade_metadata": self.grade_metadata,  # Legacy field
                "grade_results": grade_results_list,
                "job_id": self.job_id,
                "retry_count": self.retry_count,
                "can_retry": can_retry_val,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": (
                    self.completed_at.isoformat() if self.completed_at else None
                ),
            }
        except Exception as e:
            return {
                "id": getattr(self, "id", None),
                "original_filename": getattr(self, "original_filename", None),
                "status": getattr(self, "status", None),
                "error": f"Error serializing submission: {str(e)}",
            }

    def set_status(self, status, error_message=None):
        """Update submission status."""
        self.status = status
        if error_message:
            self.error_message = error_message
        self.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        # Update job progress
        if self.job:
            self.job.update_progress()

    def can_retry(self, max_retries=3):
        """Check if submission can be retried."""
        return self.status == "failed" and self.retry_count < max_retries

    def retry(self, max_retries=3):
        """Retry a failed submission."""
        if not self.can_retry(max_retries):
            return False

        self.status = "pending"
        self.error_message = None
        self.retry_count += 1
        self.updated_at = datetime.now(timezone.utc)

        # Clear previous grade results for retry
        for grade_result in self.grade_results:
            db.session.delete(grade_result)

        db.session.commit()

        # Update job status if it was failed
        if self.job and self.job.status == "failed":
            self.job.status = "pending"
            db.session.commit()

        return True

    def mark_as_processing(self):
        """Mark submission as processing."""
        self.status = "processing"
        self.started_at = datetime.now(timezone.utc)
        db.session.commit()

    def mark_as_completed(self, grade):
        """Mark submission as completed with grade."""
        self.status = "completed"
        self.grade = grade
        self.completed_at = datetime.now(timezone.utc)
        self.error_message = None
        db.session.commit()

    def mark_as_failed(self, error_message):
        """Mark submission as failed with error message."""
        self.status = "failed"
        self.error_message = error_message
        self.completed_at = datetime.now(timezone.utc)
        db.session.commit()

    def add_grade_result(
        self,
        grade,
        provider,
        model,
        status="completed",
        error_message=None,
        metadata=None,
    ):
        """Add a new grade result to this submission."""
        grade_result = GradeResult(
            grade=grade,
            provider=provider,
            model=model,
            status=status,
            error_message=error_message,
            grade_metadata=metadata,
        )
        self.grade_results.append(grade_result)
        db.session.commit()
        return grade_result


class BatchTemplate(db.Model):
    """Model for storing batch templates that can be reused."""

    __tablename__ = "batch_templates"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Template metadata
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., 'essay', 'report', 'assignment'

    # Template settings
    default_settings = db.Column(db.JSON)  # Default settings for batch creation
    job_structure = db.Column(db.JSON)  # Default job structure for batch
    processing_rules = db.Column(db.JSON)  # Processing rules for batch

    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)

    # Access control
    is_public = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(100))

    def to_dict(self):
        """Convert batch template to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "default_settings": self.default_settings,
            "job_structure": self.job_structure,
            "processing_rules": self.processing_rules,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_public": self.is_public,
            "created_by": self.created_by,
            "type": "batch",
        }

    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)
        db.session.commit()


class JobTemplate(db.Model):
    """Model for storing job templates that can be reused."""

    __tablename__ = "job_templates"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Template metadata
    name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.String(100))  # e.g., 'essay', 'report', 'assignment'

    # Job configuration
    provider = db.Column(db.String(50))  # openrouter, claude, lm_studio
    model = db.Column(db.String(100))
    prompt = db.Column(db.Text)
    temperature = db.Column(db.Float, default=0.3)
    max_tokens = db.Column(db.Integer, default=2000)
    models_to_compare = db.Column(db.JSON)  # List of models to use for comparison

    # References to saved configurations
    saved_prompt_id = db.Column(
        db.String(36), db.ForeignKey("saved_prompts.id"), nullable=True
    )
    saved_marking_scheme_id = db.Column(
        db.String(36), db.ForeignKey("saved_marking_schemes.id"), nullable=True
    )

    # Usage tracking
    usage_count = db.Column(db.Integer, default=0)
    last_used = db.Column(db.DateTime)

    # Access control
    is_public = db.Column(db.Boolean, default=False)
    created_by = db.Column(db.String(100))

    # Relationships
    saved_prompt = db.relationship("SavedPrompt", backref="job_templates", lazy=True)
    saved_marking_scheme = db.relationship(
        "SavedMarkingScheme", backref="job_templates", lazy=True
    )

    def to_dict(self):
        """Convert job template to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "provider": self.provider,
            "model": self.model,
            "prompt": self.prompt,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "models_to_compare": self.models_to_compare,
            "saved_prompt_id": self.saved_prompt_id,
            "saved_marking_scheme_id": self.saved_marking_scheme_id,
            "usage_count": self.usage_count,
            "last_used": self.last_used.isoformat() if self.last_used else None,
            "is_public": self.is_public,
            "created_by": self.created_by,
            "type": "job",
        }

    def increment_usage(self):
        """Increment usage count and update last used timestamp."""
        self.usage_count += 1
        self.last_used = datetime.now(timezone.utc)
        db.session.commit()


class JobBatch(db.Model):
    """Model for managing batch uploads with enhanced functionality."""

    __tablename__ = "job_batches"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Batch metadata
    batch_name = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    status = db.Column(
        db.String(50), default="draft"
    )  # draft, pending, processing, paused, completed, completed_with_errors, failed, cancelled, archived
    priority = db.Column(db.Integer, default=5)  # 1-10, higher is more important
    tags = db.Column(db.JSON)  # For categorization and filtering

    # Configuration
    provider = db.Column(db.String(50))  # Can be null for mixed batches
    prompt = db.Column(db.Text)  # Default prompt for batch
    model = db.Column(db.String(100))  # Default model for batch
    models_to_compare = db.Column(db.JSON)  # Default models for comparison

    # Model parameters
    temperature = db.Column(db.Float, default=0.3)
    max_tokens = db.Column(db.Integer, default=2000)

    # Advanced settings
    batch_settings = db.Column(db.JSON)  # Additional configuration
    auto_assign_jobs = db.Column(db.Boolean, default=False)  # Auto-assign new jobs

    # Progress tracking
    total_jobs = db.Column(db.Integer, default=0)
    completed_jobs = db.Column(db.Integer, default=0)
    failed_jobs = db.Column(db.Integer, default=0)

    # Timeline
    deadline = db.Column(db.DateTime)
    started_at = db.Column(db.DateTime)
    completed_at = db.Column(db.DateTime)
    estimated_completion = db.Column(db.DateTime)

    # Template reference
    template_id = db.Column(
        db.String(36), db.ForeignKey("batch_templates.id"), nullable=True
    )

    # Ownership and permissions
    created_by = db.Column(db.String(100))
    shared_with = db.Column(db.JSON)  # List of users/groups with access

    # Saved configurations references
    saved_prompt_id = db.Column(
        db.String(36), db.ForeignKey("saved_prompts.id"), nullable=True
    )
    saved_marking_scheme_id = db.Column(
        db.String(36), db.ForeignKey("saved_marking_schemes.id"), nullable=True
    )

    # Relationships
    jobs = db.relationship(
        "GradingJob", backref="batch", lazy=True, foreign_keys="GradingJob.batch_id"
    )
    template = db.relationship("BatchTemplate", backref="batches", lazy=True)

    def to_dict(self):
        """Convert batch to dictionary."""
        try:
            # Handle job-related calculations safely
            total_jobs = 0
            completed_jobs = 0
            failed_jobs = 0
            processing_jobs = 0
            pending_jobs = 0
            try:
                total_jobs = len(self.jobs)
                completed_jobs = sum(
                    1 for job in self.jobs if job.status == "completed"
                )
                failed_jobs = sum(
                    1
                    for job in self.jobs
                    if job.status in ["failed", "completed_with_errors"]
                )
                processing_jobs = sum(
                    1 for job in self.jobs if job.status == "processing"
                )
                pending_jobs = sum(1 for job in self.jobs if job.status == "pending")
            except Exception:
                pass

            template_dict = None
            try:
                template_dict = self.template.to_dict() if self.template else None
            except Exception:
                pass

            progress = 0
            try:
                progress = self.get_progress()
            except Exception:
                pass

            can_retry = False
            can_start = False
            can_pause = False
            can_resume = False
            try:
                can_retry = self.can_retry_failed_jobs()
                can_start = self.can_start()
                can_pause = self.can_pause()
                can_resume = self.can_resume()
            except Exception:
                pass

            return {
                "id": self.id,
                "created_at": self.created_at.isoformat() if self.created_at else None,
                "updated_at": self.updated_at.isoformat() if self.updated_at else None,
                "batch_name": self.batch_name,
                "description": self.description,
                "status": self.status,
                "priority": self.priority,
                "tags": self.tags or [],
                "provider": self.provider,
                "prompt": self.prompt,
                "model": self.model,
                "models_to_compare": self.models_to_compare,
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
                "batch_settings": self.batch_settings or {},
                "auto_assign_jobs": self.auto_assign_jobs,
                "total_jobs": total_jobs,
                "completed_jobs": completed_jobs,
                "failed_jobs": failed_jobs,
                "processing_jobs": processing_jobs,
                "pending_jobs": pending_jobs,
                "deadline": self.deadline.isoformat() if self.deadline else None,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "completed_at": (
                    self.completed_at.isoformat() if self.completed_at else None
                ),
                "estimated_completion": (
                    self.estimated_completion.isoformat()
                    if self.estimated_completion
                    else None
                ),
                "template_id": self.template_id,
                "template": template_dict,
                "created_by": self.created_by,
                "shared_with": self.shared_with or [],
                "saved_prompt_id": self.saved_prompt_id,
                "saved_marking_scheme_id": self.saved_marking_scheme_id,
                "progress": progress,
                "can_retry": can_retry,
                "can_start": can_start,
                "can_pause": can_pause,
                "can_resume": can_resume,
            }
        except Exception as e:
            return {
                "id": getattr(self, "id", None),
                "batch_name": getattr(self, "batch_name", None),
                "status": getattr(self, "status", None),
                "error": f"Error serializing batch: {str(e)}",
            }

    def get_progress(self):
        """Calculate batch progress percentage."""
        if not self.jobs:
            return 0
        total = len(self.jobs)
        completed = sum(
            1
            for job in self.jobs
            if job.status in ["completed", "failed", "completed_with_errors"]
        )
        return round((completed / total) * 100, 2) if total > 0 else 0

    def update_progress(self):
        """Update batch progress and status based on jobs."""
        if not self.jobs:
            return

        total = len(self.jobs)
        completed = sum(1 for job in self.jobs if job.status == "completed")
        failed = sum(
            1 for job in self.jobs if job.status in ["failed", "completed_with_errors"]
        )
        processing = sum(1 for job in self.jobs if job.status == "processing")

        self.total_jobs = total
        self.completed_jobs = completed
        self.failed_jobs = failed

        # Update batch status based on job states
        if processing > 0:
            if self.status != "paused":
                self.status = "processing"
        elif completed + failed >= total:
            if failed == 0:
                self.status = "completed"
                self.completed_at = datetime.now(timezone.utc)
            elif completed == 0:
                self.status = "failed"
            else:
                self.status = "completed_with_errors"
                self.completed_at = datetime.now(timezone.utc)

        db.session.commit()

    def can_start(self):
        """Check if batch can be started."""
        return self.status in ["draft", "pending"] and len(self.jobs) > 0

    def can_pause(self):
        """Check if batch can be paused."""
        return self.status == "processing"

    def can_resume(self):
        """Check if batch can be resumed."""
        return self.status == "paused"

    def can_retry_failed_jobs(self):
        """Check if batch has failed jobs that can be retried."""
        return any(
            job.can_retry_failed_submissions()
            for job in self.jobs
            if job.status in ["failed", "completed_with_errors"]
        )

    def start_batch(self):
        """Start processing the batch."""
        if not self.can_start():
            return False

        self.status = "processing"
        self.started_at = datetime.now(timezone.utc)

        # Queue all pending jobs for processing
        for job in self.jobs:
            if job.status == "pending":
                from tasks import process_job

                process_job.delay(job.id)

        db.session.commit()
        return True

    def pause_batch(self):
        """Pause batch processing."""
        if not self.can_pause():
            return False

        self.status = "paused"
        # Note: Individual jobs will continue but new jobs won't start
        db.session.commit()
        return True

    def resume_batch(self):
        """Resume batch processing."""
        if not self.can_resume():
            return False

        self.status = "processing"

        # Queue pending jobs for processing
        for job in self.jobs:
            if job.status == "pending":
                from tasks import process_job

                process_job.delay(job.id)

        db.session.commit()
        return True

    def cancel_batch(self):
        """Cancel batch processing."""
        if self.status in ["completed", "cancelled", "archived"]:
            return False

        self.status = "cancelled"

        # Cancel pending jobs
        for job in self.jobs:
            if job.status == "pending":
                job.status = "cancelled"

        db.session.commit()
        return True

    def retry_failed_jobs(self):
        """Retry all failed jobs in the batch."""
        retried_count = 0

        for job in self.jobs:
            if (
                job.status in ["failed", "completed_with_errors"]
                and job.can_retry_failed_submissions()
            ):
                count = job.retry_failed_submissions()
                if count > 0:
                    retried_count += 1

        if retried_count > 0:
            self.status = "processing"
            db.session.commit()

        return retried_count

    def add_job(self, job):
        """Add a job to this batch."""
        # Check if batch can accept new jobs
        if not self.can_add_jobs():
            raise ValueError(f"Cannot add jobs to batch with status '{self.status}'")

        job.batch_id = self.id

        # Apply batch defaults to job if not set
        if not job.provider and self.provider:
            job.provider = self.provider
        if not job.prompt and self.prompt:
            job.prompt = self.prompt
        if not job.model and self.model:
            job.model = self.model
        if not job.models_to_compare and self.models_to_compare:
            job.models_to_compare = self.models_to_compare
        if job.temperature is None and self.temperature is not None:
            job.temperature = self.temperature
        if job.max_tokens is None and self.max_tokens is not None:
            job.max_tokens = self.max_tokens

        # Apply saved configurations if batch has them and job doesn't
        if not job.saved_prompt_id and self.saved_prompt_id:
            job.saved_prompt_id = self.saved_prompt_id
        if not job.saved_marking_scheme_id and self.saved_marking_scheme_id:
            job.saved_marking_scheme_id = self.saved_marking_scheme_id

        db.session.commit()
        self.update_progress()

    def create_job_with_batch_settings(self, job_name, description=None, **kwargs):
        """Create a new job within this batch, inheriting batch settings."""
        from models import GradingJob  # Import here to avoid circular imports

        # Check if batch can accept new jobs
        if not self.can_add_jobs():
            raise ValueError(f"Cannot create jobs in batch with status '{self.status}'")

        # Create job with batch defaults
        job_data = {
            "job_name": job_name,
            "description": description or "",
            "provider": kwargs.get("provider") or self.provider or "openrouter",
            "prompt": kwargs.get("prompt")
            or self.prompt
            or "Please grade this document.",
            "model": kwargs.get("model") or self.model,
            "models_to_compare": kwargs.get("models_to_compare")
            or self.models_to_compare,
            "temperature": (
                kwargs.get("temperature")
                if kwargs.get("temperature") is not None
                else self.temperature
            ),
            "max_tokens": (
                kwargs.get("max_tokens")
                if kwargs.get("max_tokens") is not None
                else self.max_tokens
            ),
            "priority": kwargs.get("priority", 5),
            "saved_prompt_id": kwargs.get("saved_prompt_id") or self.saved_prompt_id,
            "saved_marking_scheme_id": kwargs.get("saved_marking_scheme_id")
            or self.saved_marking_scheme_id,
            "batch_id": self.id,
        }

        # Remove None values
        job_data = {k: v for k, v in job_data.items() if v is not None}

        # Create the job
        job = GradingJob(**job_data)
        db.session.add(job)
        db.session.commit()

        # Update batch progress
        self.update_progress()

        return job

    def get_batch_settings_summary(self):
        """Get a summary of batch settings for display/inheritance."""
        try:
            saved_prompt_name = None
            if self.saved_prompt_id:
                saved_prompt = db.session.get(SavedPrompt, self.saved_prompt_id)
                saved_prompt_name = saved_prompt.name if saved_prompt else None
        except Exception:
            saved_prompt_name = None

        try:
            saved_marking_scheme_name = None
            if self.saved_marking_scheme_id:
                saved_marking_scheme = db.session.get(
                    SavedMarkingScheme, self.saved_marking_scheme_id
                )
                saved_marking_scheme_name = (
                    saved_marking_scheme.name if saved_marking_scheme else None
                )
        except Exception:
            saved_marking_scheme_name = None

        return {
            "provider": self.provider,
            "prompt": self.prompt,
            "model": self.model,
            "models_to_compare": self.models_to_compare,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "saved_prompt_id": self.saved_prompt_id,
            "saved_marking_scheme_id": self.saved_marking_scheme_id,
            "saved_prompt_name": saved_prompt_name,
            "saved_marking_scheme_name": saved_marking_scheme_name,
        }

    def can_add_jobs(self):
        """Check if jobs can be added to this batch."""
        # Only allow adding jobs to batches that are still in an active state
        # Draft, pending, and paused batches can accept new jobs
        return self.status in ["draft", "pending", "paused"]

    def remove_job(self, job):
        """Remove a job from this batch."""
        job.batch_id = None
        db.session.commit()
        self.update_progress()

    def duplicate(self, new_name=None):
        """Create a duplicate of this batch."""
        new_batch = JobBatch(
            batch_name=new_name or f"{self.batch_name} (Copy)",
            description=self.description,
            provider=self.provider,
            prompt=self.prompt,
            model=self.model,
            models_to_compare=self.models_to_compare,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            batch_settings=self.batch_settings,
            auto_assign_jobs=self.auto_assign_jobs,
            priority=self.priority,
            tags=self.tags,
            template_id=self.template_id,
            saved_prompt_id=self.saved_prompt_id,
            saved_marking_scheme_id=self.saved_marking_scheme_id,
            created_by=self.created_by,
        )

        db.session.add(new_batch)
        db.session.commit()
        return new_batch

    def archive(self):
        """Archive this batch."""
        self.status = "archived"
        db.session.commit()


class Config(db.Model):
    """Model for storing application configuration settings with encrypted API keys."""

    __tablename__ = "config"

    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # API Configuration - Encrypted Storage
    # Use longer VARCHAR to accommodate Fernet ciphertext (longer than plaintext)
    _openrouter_api_key = db.Column('openrouter_api_key', db.String(500))
    _claude_api_key = db.Column('claude_api_key', db.String(500))
    _gemini_api_key = db.Column('gemini_api_key', db.String(500))
    _openai_api_key = db.Column('openai_api_key', db.String(500))
    _nanogpt_api_key = db.Column('nanogpt_api_key', db.String(500))
    _chutes_api_key = db.Column('chutes_api_key', db.String(500))
    _zai_api_key = db.Column('zai_api_key', db.String(500))
    zai_pricing_plan = db.Column(db.String(20), default='normal')
    lm_studio_url = db.Column(db.String(500))
    ollama_url = db.Column(db.String(500))

    # Default Settings
    default_prompt = db.Column(db.Text)

    # Default Models per Provider
    openrouter_default_model = db.Column(db.String(200))
    claude_default_model = db.Column(db.String(200))
    gemini_default_model = db.Column(db.String(200))
    openai_default_model = db.Column(db.String(200))
    nanogpt_default_model = db.Column(db.String(200))
    chutes_default_model = db.Column(db.String(200))
    zai_default_model = db.Column(db.String(200))
    lm_studio_default_model = db.Column(db.String(200))
    ollama_default_model = db.Column(db.String(200))

    # ========================================================================
    # ENCRYPTION PROPERTIES - Automatic encryption/decryption
    # ========================================================================

    @property
    def openrouter_api_key(self):
        """Get decrypted OpenRouter API key."""
        if not self._openrouter_api_key:
            return None
        from utils.encryption import decrypt_value
        try:
            return decrypt_value(self._openrouter_api_key)
        except Exception:
            return None

    @openrouter_api_key.setter
    def openrouter_api_key(self, value):
        """Set OpenRouter API key (automatically encrypted)."""
        if not value:
            self._openrouter_api_key = None
        else:
            from utils.encryption import encrypt_value
            self._openrouter_api_key = encrypt_value(value)

    @property
    def claude_api_key(self):
        """Get decrypted Claude API key."""
        if not self._claude_api_key:
            return None
        from utils.encryption import decrypt_value
        try:
            return decrypt_value(self._claude_api_key)
        except Exception:
            return None

    @claude_api_key.setter
    def claude_api_key(self, value):
        """Set Claude API key (automatically encrypted)."""
        if not value:
            self._claude_api_key = None
        else:
            from utils.encryption import encrypt_value
            self._claude_api_key = encrypt_value(value)

    @property
    def gemini_api_key(self):
        """Get decrypted Gemini API key."""
        if not self._gemini_api_key:
            return None
        from utils.encryption import decrypt_value
        try:
            return decrypt_value(self._gemini_api_key)
        except Exception:
            return None

    @gemini_api_key.setter
    def gemini_api_key(self, value):
        """Set Gemini API key (automatically encrypted)."""
        if not value:
            self._gemini_api_key = None
        else:
            from utils.encryption import encrypt_value
            self._gemini_api_key = encrypt_value(value)

    @property
    def openai_api_key(self):
        """Get decrypted OpenAI API key."""
        if not self._openai_api_key:
            return None
        from utils.encryption import decrypt_value
        try:
            return decrypt_value(self._openai_api_key)
        except Exception:
            return None

    @openai_api_key.setter
    def openai_api_key(self, value):
        """Set OpenAI API key (automatically encrypted)."""
        if not value:
            self._openai_api_key = None
        else:
            from utils.encryption import encrypt_value
            self._openai_api_key = encrypt_value(value)

    @property
    def nanogpt_api_key(self):
        """Get decrypted NanoGPT API key."""
        if not self._nanogpt_api_key:
            return None
        from utils.encryption import decrypt_value
        try:
            return decrypt_value(self._nanogpt_api_key)
        except Exception:
            return None

    @nanogpt_api_key.setter
    def nanogpt_api_key(self, value):
        """Set NanoGPT API key (automatically encrypted)."""
        if not value:
            self._nanogpt_api_key = None
        else:
            from utils.encryption import encrypt_value
            self._nanogpt_api_key = encrypt_value(value)

    @property
    def chutes_api_key(self):
        """Get decrypted Chutes API key."""
        if not self._chutes_api_key:
            return None
        from utils.encryption import decrypt_value
        try:
            return decrypt_value(self._chutes_api_key)
        except Exception:
            return None

    @chutes_api_key.setter
    def chutes_api_key(self, value):
        """Set Chutes API key (automatically encrypted)."""
        if not value:
            self._chutes_api_key = None
        else:
            from utils.encryption import encrypt_value
            self._chutes_api_key = encrypt_value(value)

    @property
    def zai_api_key(self):
        """Get decrypted Z.AI API key."""
        if not self._zai_api_key:
            return None
        from utils.encryption import decrypt_value
        try:
            return decrypt_value(self._zai_api_key)
        except Exception:
            return None

    @zai_api_key.setter
    def zai_api_key(self, value):
        """Set Z.AI API key (automatically encrypted)."""
        if not value:
            self._zai_api_key = None
        else:
            from utils.encryption import encrypt_value
            self._zai_api_key = encrypt_value(value)

    def to_dict(self):
        """Convert config to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "openrouter_api_key": self.openrouter_api_key,
            "claude_api_key": self.claude_api_key,
            "gemini_api_key": self.gemini_api_key,
            "openai_api_key": self.openai_api_key,
            "lm_studio_url": self.lm_studio_url,
            "ollama_url": self.ollama_url,
            "default_prompt": self.default_prompt,
            "openrouter_default_model": self.openrouter_default_model,
            "claude_default_model": self.claude_default_model,
            "gemini_default_model": self.gemini_default_model,
            "openai_default_model": self.openai_default_model,
            "lm_studio_default_model": self.lm_studio_default_model,
            "ollama_default_model": self.ollama_default_model,
        }

    @staticmethod
    def get_or_create():
        """Get existing config or create a new one."""
        config = Config.query.first()
        if not config:
            config = Config()
            db.session.add(config)
            db.session.commit()
        return config

    def get_default_model(self, provider):
        """Get the configured default model for a provider."""
        model_field_map = {
            "openrouter": self.openrouter_default_model,
            "claude": self.claude_default_model,
            "gemini": self.gemini_default_model,
            "openai": self.openai_default_model,
            "nanogpt": self.nanogpt_default_model,
            "chutes": self.chutes_default_model,
            "zai": self.zai_default_model,
            "lm_studio": self.lm_studio_default_model,
            "ollama": self.ollama_default_model,
        }

        configured_model = model_field_map.get(provider)
        if configured_model:
            return configured_model

        # Fall back to hardcoded defaults if not configured
        fallback_defaults = {
            "openrouter": "anthropic/claude-sonnet-4",
            "claude": "claude-3.5-sonnet-20241022",
            "gemini": "gemini-2.0-flash-exp",
            "openai": "gpt-4o",
            "nanogpt": "gpt-4o",
            "chutes": "gpt-4o",
            "zai": "glm-4.6",
            "lm_studio": "local-model",
            "ollama": "llama2",
        }

        return fallback_defaults.get(provider, "anthropic/claude-3-5-sonnet-20241022")


class ImageSubmission(db.Model):
    """Model for tracking image submissions (screenshots, diagrams)."""

    __tablename__ = "image_submissions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to existing submission
    submission_id = db.Column(
        db.String(36), db.ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False
    )

    # File storage (UUID-based two-level hashing)
    storage_path = db.Column(db.String(500), nullable=False)
    file_uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))

    # File metadata
    original_filename = db.Column(db.String(255), nullable=False)
    file_size_bytes = db.Column(db.Integer, nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    file_extension = db.Column(db.String(10), nullable=False)

    # Image properties
    width_pixels = db.Column(db.Integer)
    height_pixels = db.Column(db.Integer)
    aspect_ratio = db.Column(db.Numeric(5, 2))
    file_hash = db.Column(db.String(64))

    # Processing status
    processing_status = db.Column(db.String(50), default="uploaded")
    ocr_started_at = db.Column(db.DateTime)
    ocr_completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)

    # Validation status
    passes_quality_check = db.Column(db.Boolean)
    requires_manual_review = db.Column(db.Boolean, default=False)

    # Relationships
    submission = db.relationship("Submission", backref="image_submissions", lazy=True)
    extracted_content = db.relationship(
        "ExtractedContent", backref="image_submission", uselist=False, cascade="all, delete-orphan"
    )
    quality_metrics = db.relationship(
        "ImageQualityMetrics", backref="image_submission", uselist=False, cascade="all, delete-orphan"
    )

    # Indexes
    __table_args__ = (
        db.Index("idx_submission_id", "submission_id"),
        db.Index("idx_processing_status", "processing_status"),
        db.Index("idx_file_uuid", "file_uuid"),
        db.Index("idx_created_at", "created_at"),
    )

    def to_dict(self):
        """Convert image submission to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "submission_id": self.submission_id,
            "storage_path": self.storage_path,
            "file_uuid": self.file_uuid,
            "original_filename": self.original_filename,
            "file_size_bytes": self.file_size_bytes,
            "mime_type": self.mime_type,
            "file_extension": self.file_extension,
            "width_pixels": self.width_pixels,
            "height_pixels": self.height_pixels,
            "aspect_ratio": float(self.aspect_ratio) if self.aspect_ratio else None,
            "file_hash": self.file_hash,
            "processing_status": self.processing_status,
            "ocr_started_at": self.ocr_started_at.isoformat() if self.ocr_started_at else None,
            "ocr_completed_at": self.ocr_completed_at.isoformat() if self.ocr_completed_at else None,
            "error_message": self.error_message,
            "passes_quality_check": self.passes_quality_check,
            "requires_manual_review": self.requires_manual_review,
        }


class ExtractedContent(db.Model):
    """Model for storing OCR-extracted text and metadata."""

    __tablename__ = "extracted_content"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship (one-to-one with ImageSubmission)
    image_submission_id = db.Column(
        db.String(36),
        db.ForeignKey("image_submissions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # OCR results
    extracted_text = db.Column(db.Text)
    text_length = db.Column(db.Integer)
    line_count = db.Column(db.Integer)

    # OCR metadata
    ocr_provider = db.Column(db.String(50), nullable=False)
    ocr_model = db.Column(db.String(100))
    confidence_score = db.Column(db.Numeric(5, 4))
    processing_time_ms = db.Column(db.Integer)

    # Structured data
    text_regions = db.Column(db.JSON)

    # Usage tracking
    api_cost_usd = db.Column(db.Numeric(10, 6))

    # Indexes
    __table_args__ = (
        db.Index("idx_extracted_content_image_submission", "image_submission_id"),
        db.Index("idx_confidence_score", "confidence_score"),
        db.Index("idx_ocr_provider", "ocr_provider"),
    )

    def to_dict(self):
        """Convert extracted content to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "image_submission_id": self.image_submission_id,
            "extracted_text": self.extracted_text,
            "text_length": self.text_length,
            "line_count": self.line_count,
            "ocr_provider": self.ocr_provider,
            "ocr_model": self.ocr_model,
            "confidence_score": float(self.confidence_score) if self.confidence_score else None,
            "processing_time_ms": self.processing_time_ms,
            "text_regions": self.text_regions,
            "api_cost_usd": float(self.api_cost_usd) if self.api_cost_usd else None,
        }


class ImageQualityMetrics(db.Model):
    """Model for storing automated quality assessment results."""

    __tablename__ = "image_quality_metrics"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship (one-to-one with ImageSubmission)
    image_submission_id = db.Column(
        db.String(36),
        db.ForeignKey("image_submissions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )

    # Overall assessment
    overall_quality = db.Column(db.String(20), nullable=False)
    passes_quality_check = db.Column(db.Boolean, nullable=False, default=False)

    # Blur detection
    blur_score = db.Column(db.Numeric(10, 2))
    is_blurry = db.Column(db.Boolean)
    blur_threshold = db.Column(db.Numeric(10, 2))

    # Resolution metrics
    meets_min_resolution = db.Column(db.Boolean)
    min_width_required = db.Column(db.Integer)
    min_height_required = db.Column(db.Integer)

    # Completeness assessment
    edge_density_top = db.Column(db.Numeric(5, 2))
    edge_density_bottom = db.Column(db.Numeric(5, 2))
    edge_density_left = db.Column(db.Numeric(5, 2))
    edge_density_right = db.Column(db.Numeric(5, 2))
    avg_edge_density = db.Column(db.Numeric(5, 2))
    max_edge_density = db.Column(db.Numeric(5, 2))
    likely_cropped = db.Column(db.Boolean)

    # Quality issues
    issues = db.Column(db.JSON)

    # Processing metadata
    assessment_duration_ms = db.Column(db.Integer)

    # Indexes
    __table_args__ = (
        db.Index("idx_image_quality_image_submission", "image_submission_id"),
        db.Index("idx_overall_quality", "overall_quality"),
        db.Index("idx_passes_quality_check", "passes_quality_check"),
    )

    def to_dict(self):
        """Convert image quality metrics to dictionary."""
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "image_submission_id": self.image_submission_id,
            "overall_quality": self.overall_quality,
            "passes_quality_check": self.passes_quality_check,
            "blur_score": float(self.blur_score) if self.blur_score else None,
            "is_blurry": self.is_blurry,
            "blur_threshold": float(self.blur_threshold) if self.blur_threshold else None,
            "meets_min_resolution": self.meets_min_resolution,
            "min_width_required": self.min_width_required,
            "min_height_required": self.min_height_required,
            "edge_density_top": float(self.edge_density_top) if self.edge_density_top else None,
            "edge_density_bottom": float(self.edge_density_bottom) if self.edge_density_bottom else None,
            "edge_density_left": float(self.edge_density_left) if self.edge_density_left else None,
            "edge_density_right": float(self.edge_density_right) if self.edge_density_right else None,
            "avg_edge_density": float(self.avg_edge_density) if self.avg_edge_density else None,
            "max_edge_density": float(self.max_edge_density) if self.max_edge_density else None,
            "likely_cropped": self.likely_cropped,
            "issues": self.issues,
            "assessment_duration_ms": self.assessment_duration_ms,
        }
