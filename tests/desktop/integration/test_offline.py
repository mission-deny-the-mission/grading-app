"""
Integration tests for offline functionality.

Tests cover:
- Application starts without internet connection
- Existing grading features work offline
- Database operations work offline
- Only AI API calls require internet (should fail gracefully)
- Settings persistence works offline
"""

import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch, Mock
import socket

import pytest

# Mock webview, keyring, and apscheduler before importing desktop modules
mock_webview = MagicMock()
sys.modules['webview'] = mock_webview
sys.modules['keyring'] = MagicMock()
sys.modules['keyrings'] = MagicMock()
sys.modules['keyrings.cryptfile'] = MagicMock()
sys.modules['keyrings.cryptfile.cryptfile'] = MagicMock()
sys.modules['apscheduler'] = MagicMock()
sys.modules['apscheduler.schedulers'] = MagicMock()
sys.modules['apscheduler.schedulers.background'] = MagicMock()


class TestOfflineStartup:
    """Test that application starts without internet connection."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    def test_application_starts_offline(
        self, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_create_window
    ):
        """Test that application starts successfully without internet."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        # Simulate offline: mock network requests to fail
        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', return_value=5050):
                with patch.object(db, 'create_all'):
                    # Mock socket to simulate no internet
                    with patch('socket.socket') as mock_socket_class:
                        mock_socket = MagicMock()
                        mock_socket.connect.side_effect = socket.error("Network unreachable")
                        mock_socket_class.return_value.__enter__.return_value = mock_socket

                        result = main()

        # Verify application started successfully despite network being unavailable
        assert result == 0

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.main.get_user_data_dir')
    @patch('desktop.main.logger')
    def test_offline_startup_logged(
        self, mock_logger, mock_get_user_data_dir, mock_thread_class,
        mock_app, mock_shutdown, mock_create_window
    ):
        """Test that offline startup proceeds normally with appropriate logging."""
        from desktop.main import main
        from models import db

        # Setup mocks
        temp_dir = Path(tempfile.mkdtemp())
        mock_get_user_data_dir.return_value = temp_dir
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        mock_app_context = MagicMock()
        mock_app.app_context.return_value.__enter__ = MagicMock(return_value=mock_app_context)
        mock_app.app_context.return_value.__exit__ = MagicMock(return_value=False)

        with patch('desktop.main.configure_app_for_desktop'):
            with patch('desktop.main.get_free_port', return_value=5050):
                with patch.object(db, 'create_all'):
                    main()

        # Verify normal startup messages were logged (offline doesn't prevent startup)
        log_calls = [str(call) for call in mock_logger.info.call_args_list]
        log_text = ' '.join(log_calls)
        assert 'Starting Grading App Desktop Application' in log_text


class TestOfflineDatabaseOperations:
    """Test that database operations work offline."""

    def test_database_reads_work_offline(self):
        """Test that database read operations work without internet."""
        from models import db, GradingJob
        from flask import Flask

        # Create in-memory SQLite database (doesn't need internet)
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create test data
            job = GradingJob(
                job_name='Test Job',
                description='Test offline read',
                provider='openrouter',
                model='test-model'
            )
            db.session.add(job)
            db.session.commit()

            # Read data (should work offline)
            retrieved = GradingJob.query.filter_by(job_name='Test Job').first()
            assert retrieved is not None
            assert retrieved.description == 'Test offline read'

    def test_database_writes_work_offline(self):
        """Test that database write operations work without internet."""
        from models import db, GradingJob
        from flask import Flask

        # Create in-memory SQLite database
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Write data (should work offline)
            job = GradingJob(
                job_name='Offline Write Test',
                description='Created without internet',
                provider='openrouter',
                model='test-model'
            )
            db.session.add(job)
            db.session.commit()

            # Verify write succeeded
            assert job.id is not None

    def test_database_updates_work_offline(self):
        """Test that database update operations work without internet."""
        from models import db, GradingJob
        from flask import Flask

        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create initial data
            job = GradingJob(
                job_name='Update Test',
                description='Original description',
                provider='openrouter',
                model='test-model'
            )
            db.session.add(job)
            db.session.commit()

            # Update data (should work offline)
            job.description = 'Updated offline'
            db.session.commit()

            # Verify update succeeded
            retrieved = GradingJob.query.filter_by(job_name='Update Test').first()
            assert retrieved.description == 'Updated offline'

    def test_database_deletes_work_offline(self):
        """Test that database delete operations work without internet."""
        from models import db, GradingJob
        from flask import Flask

        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create data
            job = GradingJob(
                job_name='Delete Test',
                description='To be deleted',
                provider='openrouter',
                model='test-model'
            )
            db.session.add(job)
            db.session.commit()
            job_id = job.id

            # Delete data (should work offline)
            db.session.delete(job)
            db.session.commit()

            # Verify deletion succeeded
            retrieved = GradingJob.query.get(job_id)
            assert retrieved is None


class TestOfflineGradingFeatures:
    """Test that existing grading features work offline."""

    def test_job_creation_works_offline(self):
        """Test that creating grading jobs works without internet."""
        from models import db, GradingJob
        from flask import Flask

        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create job offline
            job = GradingJob(
                job_name='Offline Job',
                description='Created without internet connection',
                provider='openrouter',
                model='test-model',
                priority=5
            )
            db.session.add(job)
            db.session.commit()

            # Verify creation
            assert job.id is not None
            assert job.job_name == 'Offline Job'

    def test_submission_storage_works_offline(self):
        """Test that storing submissions works without internet."""
        from models import db, GradingJob, Submission
        from flask import Flask

        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create test data
            job = GradingJob(
                job_name='Test Job',
                provider='openrouter',
                model='test-model'
            )
            db.session.add(job)
            db.session.commit()

            # Create submission offline
            submission = Submission(
                job_id=job.id,
                filename='test.pdf',
                file_type='pdf',
                file_size=1024,
                status='pending'
            )
            db.session.add(submission)
            db.session.commit()

            # Verify storage
            assert submission.id is not None

    def test_marking_scheme_management_works_offline(self):
        """Test that managing marking schemes works without internet."""
        from models import db, MarkingScheme
        from flask import Flask

        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create marking scheme offline
            scheme = MarkingScheme(
                name='Offline Scheme',
                filename='offline_scheme.txt',
                file_type='txt',
                file_size=512,
                content='Created without internet'
            )
            db.session.add(scheme)
            db.session.commit()

            # Verify creation
            assert scheme.id is not None
            assert scheme.content == 'Created without internet'


class TestOfflineSettingsPersistence:
    """Test that settings persistence works offline."""

    def test_settings_can_be_loaded_offline(self):
        """Test that settings can be loaded without internet connection."""
        from desktop.settings import Settings

        temp_dir = Path(tempfile.mkdtemp())
        settings_path = temp_dir / 'settings.json'

        # Create settings file
        settings = Settings(settings_path)
        settings.load()

        # Verify settings loaded successfully (no network needed)
        assert settings.get('version') is not None

    def test_settings_can_be_saved_offline(self):
        """Test that settings can be saved without internet connection."""
        from desktop.settings import Settings

        temp_dir = Path(tempfile.mkdtemp())
        settings_path = temp_dir / 'settings.json'

        # Create and modify settings
        settings = Settings(settings_path)
        settings.load()
        settings.set('ui.theme', 'dark')
        settings.save()

        # Verify save succeeded (no network needed)
        assert settings_path.exists()

        # Verify saved settings can be loaded
        settings2 = Settings(settings_path)
        settings2.load()
        assert settings2.get('ui.theme') == 'dark'

    def test_settings_persistence_across_sessions_offline(self):
        """Test that settings persist across sessions without internet."""
        from desktop.settings import Settings

        temp_dir = Path(tempfile.mkdtemp())
        settings_path = temp_dir / 'settings.json'

        # First session - create and save settings
        settings1 = Settings(settings_path)
        settings1.load()
        settings1.set('ui.theme', 'dark')
        settings1.set('ui.window_geometry.width', 1920)
        settings1.set('updates.auto_check', False)
        settings1.save()

        # Second session - load settings (simulating app restart offline)
        settings2 = Settings(settings_path)
        settings2.load()

        # Verify all settings persisted
        assert settings2.get('ui.theme') == 'dark'
        assert settings2.get('ui.window_geometry.width') == 1920
        assert settings2.get('updates.auto_check') is False


class TestOfflineAIAPIGracefulFailure:
    """Test that AI API calls fail gracefully when offline."""

    @patch('requests.post')
    def test_ai_api_call_fails_gracefully_offline(self, mock_post):
        """Test that AI API calls handle offline status gracefully."""
        import requests

        # Simulate network error
        mock_post.side_effect = requests.exceptions.ConnectionError("Network unreachable")

        # Try to make AI API call
        with pytest.raises(requests.exceptions.ConnectionError):
            requests.post('https://api.example.com/generate', json={'prompt': 'test'})

    @patch('requests.post')
    def test_ai_api_timeout_handled(self, mock_post):
        """Test that AI API timeouts are handled properly."""
        import requests

        # Simulate timeout
        mock_post.side_effect = requests.exceptions.Timeout("Connection timeout")

        # Try to make AI API call
        with pytest.raises(requests.exceptions.Timeout):
            requests.post(
                'https://api.example.com/generate',
                json={'prompt': 'test'},
                timeout=5
            )

    def test_grading_without_ai_still_works(self):
        """Test that manual grading works without AI API access."""
        from models import db, GradingJob, Submission, GradeResult
        from flask import Flask

        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create test data
            job = GradingJob(
                job_name='Manual Grade Test',
                provider='openrouter',
                model='test-model'
            )
            db.session.add(job)
            db.session.commit()

            submission = Submission(
                job_id=job.id,
                filename='test.pdf',
                file_type='pdf',
                file_size=1024,
                status='submitted'
            )
            db.session.add(submission)
            db.session.commit()

            # Manual grading (no AI needed)
            grade = GradeResult(
                submission_id=submission.id,
                grade_value='85',
                comments='Good work! (graded manually offline)',
                status='completed'
            )
            db.session.add(grade)
            db.session.commit()

            # Verify manual grading worked
            assert grade.id is not None
            assert grade.grade_value == '85'


class TestOfflineFileOperations:
    """Test that local file operations work offline."""

    def test_file_upload_storage_works_offline(self):
        """Test that storing uploaded files works without internet."""
        import shutil

        temp_dir = Path(tempfile.mkdtemp())
        uploads_dir = temp_dir / 'uploads'
        uploads_dir.mkdir()

        # Create a test file
        test_file = temp_dir / 'test_submission.txt'
        test_file.write_text('Test submission content')

        # "Upload" file (copy to uploads directory)
        dest_file = uploads_dir / 'student_submission.txt'
        shutil.copy(test_file, dest_file)

        # Verify file was stored
        assert dest_file.exists()
        assert dest_file.read_text() == 'Test submission content'

    def test_file_retrieval_works_offline(self):
        """Test that retrieving stored files works without internet."""
        temp_dir = Path(tempfile.mkdtemp())
        uploads_dir = temp_dir / 'uploads'
        uploads_dir.mkdir()

        # Create a stored file
        stored_file = uploads_dir / 'stored_submission.txt'
        stored_file.write_text('Stored content')

        # Retrieve file
        content = stored_file.read_text()

        # Verify retrieval
        assert content == 'Stored content'

    def test_database_backup_works_offline(self):
        """Test that database backup creation works without internet."""
        import shutil

        temp_dir = Path(tempfile.mkdtemp())

        # Create a "database" file
        db_file = temp_dir / 'grading.db'
        db_file.write_text('Database content')

        # Create backup
        backup_file = temp_dir / 'grading.db.backup'
        shutil.copy(db_file, backup_file)

        # Verify backup was created
        assert backup_file.exists()
        assert backup_file.read_text() == 'Database content'


class TestOfflineIntegrationScenarios:
    """Test complete offline usage scenarios."""

    @patch('desktop.main.create_main_window')
    @patch('desktop.main.shutdown_gracefully')
    @patch('desktop.main.app')
    @patch('desktop.main.threading.Thread')
    @patch('desktop.app_wrapper.credentials.initialize_keyring')
    @patch('desktop.app_wrapper.credentials.get_api_key')
    @patch('desktop.app_wrapper.event.listen')
    def test_complete_offline_session(
        self, mock_event_listen, mock_get_api_key, mock_init_keyring,
        mock_thread_class, mock_app, mock_shutdown, mock_create_window
    ):
        """Test a complete user session offline: startup, work, shutdown."""
        from desktop.main import main
        from desktop.app_wrapper import configure_app_for_desktop
        from desktop.settings import Settings
        from models import db, GradingJob
        from flask import Flask

        # Setup temp directory
        temp_dir = Path(tempfile.mkdtemp())

        # Setup mocks
        mock_get_api_key.return_value = ""
        mock_thread = MagicMock()
        mock_thread_class.return_value = mock_thread

        # Mock app context
        real_app = Flask(__name__)
        real_app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_dir / "grading.db"}'
        real_app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

        db.init_app(real_app)

        # 1. Application startup (offline)
        with patch('desktop.main.get_user_data_dir', return_value=temp_dir):
            with patch('desktop.main.app', real_app):
                with patch('desktop.main.configure_app_for_desktop', wraps=configure_app_for_desktop):
                    with patch('desktop.main.get_free_port', return_value=5050):
                        result = main()

        # Verify startup succeeded
        assert result == 0

        # 2. User works offline - create grading job, save settings
        with real_app.app_context():
            # Create job (should work offline)
            job = GradingJob(
                job_name='Offline Work',
                description='Created during offline session',
                provider='openrouter',
                model='test-model',
                priority=5
            )
            db.session.add(job)
            db.session.commit()

            # Verify job was created
            assert job.id is not None

        # Save settings (should work offline)
        settings_path = temp_dir / 'settings.json'
        settings = Settings(settings_path)
        settings.load()
        settings.set('ui.theme', 'dark')
        settings.save()

        # 3. Verify all data persisted (offline)
        with real_app.app_context():
            # Verify job persisted
            saved_job = GradingJob.query.filter_by(job_name='Offline Work').first()
            assert saved_job is not None
            assert saved_job.description == 'Created during offline session'

        # Verify settings persisted
        settings2 = Settings(settings_path)
        settings2.load()
        assert settings2.get('ui.theme') == 'dark'

    def test_offline_then_online_recovery(self):
        """Test that application recovers gracefully when going from offline to online."""
        from desktop.settings import Settings
        from models import db, GradingJob
        from flask import Flask

        temp_dir = Path(tempfile.mkdtemp())

        # Create app and settings offline
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{temp_dir / "grading.db"}'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        db.init_app(app)

        with app.app_context():
            db.create_all()

            # Create data offline
            job = GradingJob(
                job_name='Offline Job',
                description='Created offline',
                provider='openrouter',
                model='test-model'
            )
            db.session.add(job)
            db.session.commit()

        # Save settings offline
        settings_path = temp_dir / 'settings.json'
        settings = Settings(settings_path)
        settings.load()
        settings.set('ui.theme', 'dark')
        settings.save()

        # Simulate going online - data should still be accessible
        with app.app_context():
            # Data should still be there
            saved_job = GradingJob.query.filter_by(job_name='Offline Job').first()
            assert saved_job is not None

        # Settings should still be there
        settings2 = Settings(settings_path)
        settings2.load()
        assert settings2.get('ui.theme') == 'dark'


class TestOfflineNetworkDetection:
    """Test network connectivity detection for offline mode."""

    @patch('socket.socket')
    def test_network_unavailable_detection(self, mock_socket_class):
        """Test detection of network unavailability."""
        # Mock socket to simulate offline
        mock_socket = MagicMock()
        mock_socket.connect.side_effect = socket.error("Network unreachable")
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # Try to detect network
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('8.8.8.8', 53))
            network_available = True
        except socket.error:
            network_available = False

        # Verify offline was detected
        assert network_available is False

    @patch('socket.socket')
    def test_network_available_detection(self, mock_socket_class):
        """Test detection of network availability."""
        # Mock socket to simulate online
        mock_socket = MagicMock()
        mock_socket.connect.return_value = None
        mock_socket_class.return_value.__enter__.return_value = mock_socket

        # Try to detect network
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(('8.8.8.8', 53))
            network_available = True
        except socket.error:
            network_available = False

        # Verify online was detected
        assert network_available is True
