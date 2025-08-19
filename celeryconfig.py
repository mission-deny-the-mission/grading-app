# Celery Configuration

# Broker settings
broker_url = 'redis://localhost:6379/0'
result_backend = 'redis://localhost:6379/0'

# Task settings
task_serializer = 'json'
accept_content = ['json']
result_serializer = 'json'
timezone = 'UTC'
enable_utc = True

# Worker settings
worker_prefetch_multiplier = 1
worker_max_tasks_per_child = 1000
worker_disable_rate_limits = False

# Task routing
task_routes = {
    'tasks.process_job': {'queue': 'grading'},
    'tasks.process_batch': {'queue': 'grading'},
    'tasks.cleanup_old_files': {'queue': 'maintenance'}
}

# Task result settings
task_ignore_result = False
task_store_errors_even_if_ignored = True

# Beat schedule for periodic tasks
beat_schedule = {
    'cleanup-old-files': {
        'task': 'tasks.cleanup_old_files',
        'schedule': 3600.0,  # Run every hour
    },
}
