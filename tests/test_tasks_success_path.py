"""
Test a successful processing path for a submission using
tasks.process_submission_sync.
"""

import os
from unittest.mock import MagicMock, patch

from models import GradingJob, Submission, db
from tasks import process_submission_sync


def test_process_submission_sync_success(app, tmp_path):
    """Test successful submission processing with LM Studio provider."""
    # Create a job and a submission
    with app.app_context():
        job = GradingJob(job_name="Job Success", provider="LM Studio", prompt="Please grade.")
        db.session.add(job)
        db.session.commit()

        # Ensure file is created inside the app's upload folder
        upload_folder = app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_folder, exist_ok=True)
        file_name = "doc.txt"
        disk_path = os.path.join(upload_folder, file_name)
        with open(disk_path, "w") as f:
            f.write("Hello, this is content to grade.")

        submission = Submission(
            job_id=job.id,
            filename=file_name,
            original_filename=file_name,
            file_type="txt",
            status="pending",
        )
        db.session.add(submission)
        db.session.commit()
        sid = submission.id

    # Mock LM Studio call to return a successful grade
    fake_resp = MagicMock(status_code=200)
    fake_resp.json.return_value = {
        "choices": [{"message": {"content": "Great work! Grade: A"}}],
        "usage": {"prompt_tokens": 10, "completion_tokens": 20},
    }

    with patch("utils.llm_providers.requests.post", return_value=fake_resp):
        result = process_submission_sync(sid)
        assert result is True

    # Verify submission status updated to completed
    with app.app_context():
        refreshed = db.session.get(Submission, sid)
        assert refreshed.status == "completed"
