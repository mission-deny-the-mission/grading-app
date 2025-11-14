#!/usr/bin/env python3
"""
Script to clean up stuck jobs and restart Celery workers
"""

import subprocess
import sys
import time


def kill_celery_workers():
    """Kill all running Celery workers gracefully."""
    print("🔄 Stopping Celery workers...")

    try:
        # Get list of Celery worker processes
        result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
        celery_pids = []

        for line in result.stdout.split('\n'):
            if 'celery.*worker' in line and 'grep' not in line:
                pid = line.split()[1]
                celery_pids.append(pid)

        if celery_pids:
            print(f"Found Celery workers: {celery_pids}")

            # Try graceful shutdown first
            for pid in celery_pids:
                try:
                    subprocess.run(['kill', pid], check=True)
                    print(f"Sent SIGTERM to worker {pid}")
                except subprocess.CalledProcessError:
                    pass

            # Wait a moment
            time.sleep(3)

            # Force kill any remaining workers
            for pid in celery_pids:
                try:
                    subprocess.run(['kill', '-0', pid], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    subprocess.run(['kill', '-9', pid], check=True)
                    print(f"Force killed worker {pid}")
                except subprocess.CalledProcessError:
                    pass
        else:
            print("No Celery workers found")

    except Exception as e:
        print(f"Error stopping workers: {e}")


def clear_redis_queue():
    """Clear the Celery task queue in Redis."""
    print("🧹 Clearing Redis queues...")

    try:
        # Clear default queues
        queues = ['celery', 'grading', 'maintenance']
        redis_cmd = ['redis-cli']

        for queue in queues:
            try:
                result = subprocess.run(redis_cmd + ['del', queue], capture_output=True, text=True)
                if result.stdout.strip() != '0':
                    print(f"Cleared queue: {queue}")
            except Exception as e:
                print(f"Could not clear queue {queue}: {e}")

    except Exception as e:
        print(f"Error clearing Redis: {e}")


def restart_celery_workers():
    """Restart Celery workers."""
    print("🚀 Starting Celery workers...")

    try:
        # Start Celery workers with proper configuration
        cmd = [
            sys.executable, '-m', 'celery',
            '-A', 'tasks',
            'worker',
            '--loglevel=info',
            '--concurrency=2',
            '--queues=grading,maintenance'
        ]

        # Start workers in background
        subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for workers to start
        time.sleep(2)

        print("✅ Celery workers restarted")

    except Exception as e:
        print(f"Error starting workers: {e}")


def main():
    """Main cleanup function."""
    print("🧹 Cleaning up stuck jobs and restarting services...")

    # 1. Kill existing workers
    kill_celery_workers()

    # 2. Clear Redis queues
    clear_redis_queue()

    # 3. Restart workers
    restart_celery_workers()

    print("✅ Cleanup complete!")
    print("\n💡 To avoid this issue in the future:")
    print("   - Ensure all test files properly mock API calls")
    print("   - Don't run trigger_job.py or other scripts that queue real tasks during testing")
    print("   - Use proper test isolation and cleanup")


if __name__ == "__main__":
    main()
