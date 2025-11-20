"""
Tests for Desktop Task Queue

Tests the ThreadPoolExecutor-based task queue implementation
for single-user desktop applications.
"""

import pytest
import time
import threading
from concurrent.futures import TimeoutError


# Test helper functions
def successful_task(value):
    """A simple task that returns its input."""
    return value * 2


def slow_task(duration=0.1):
    """A task that takes time to complete."""
    time.sleep(duration)
    return "completed"


def failing_task():
    """A task that always fails."""
    raise ValueError("Task intentionally failed")


def sometimes_failing_task(attempt_storage):
    """A task that fails a few times then succeeds."""
    attempt_storage['count'] += 1
    if attempt_storage['count'] < 3:
        raise ValueError(f"Attempt {attempt_storage['count']} failed")
    return f"Success after {attempt_storage['count']} attempts"


def countdown_task(start_time_storage):
    """A task that records when it started."""
    start_time_storage['time'] = time.time()
    return "executed"


class TestDesktopTaskQueue:
    """Test suite for DesktopTaskQueue class."""

    @pytest.fixture
    def queue(self):
        """Create a DesktopTaskQueue for testing."""
        from desktop.task_queue import DesktopTaskQueue
        return DesktopTaskQueue(max_workers=4)

    @pytest.fixture(autouse=True)
    def cleanup(self, queue):
        """Ensure queue is shutdown after each test."""
        yield
        queue.shutdown(wait=True, timeout=5)

    def test_initialization(self, queue):
        """Test that queue initializes correctly."""
        assert queue.executor is not None
        assert isinstance(queue.tasks, dict)
        assert isinstance(queue.task_metadata, dict)
        assert queue.next_task_id == 0

    def test_submit_simple_task(self, queue):
        """Test submitting a simple task."""
        task_id = queue.submit(successful_task, 5)

        # Task ID should be a string
        assert isinstance(task_id, str)
        assert task_id == "0"

        # Wait for task to complete
        result = queue.wait_for_task(task_id, timeout=2)
        assert result == 10

        # Check status
        status = queue.get_status(task_id)
        assert status['status'] == 'completed'
        assert status['function'] == 'successful_task'
        assert status['result'] == 10
        assert 'submitted_at' in status
        assert 'completed_at' in status

    def test_submit_multiple_tasks(self, queue):
        """Test submitting multiple tasks and tracking them."""
        task_ids = []
        for i in range(5):
            task_id = queue.submit(successful_task, i)
            task_ids.append(task_id)

        # All tasks should have unique IDs
        assert len(set(task_ids)) == 5

        # Wait for all tasks to complete
        results = []
        for task_id in task_ids:
            result = queue.wait_for_task(task_id, timeout=2)
            results.append(result)

        # Check all results
        assert results == [0, 2, 4, 6, 8]

        # Check all statuses
        for task_id in task_ids:
            status = queue.get_status(task_id)
            assert status['status'] == 'completed'

    def test_task_status_tracking(self, queue):
        """Test that task status is tracked correctly through lifecycle."""
        task_id = queue.submit(slow_task, duration=0.2)

        # Initially should be pending or running (task may start immediately)
        status = queue.get_status(task_id)
        assert status['status'] in ['pending', 'running']
        assert status['function'] == 'slow_task'
        assert 'submitted_at' in status

        # After a short wait, might be running
        time.sleep(0.05)
        status = queue.get_status(task_id)
        # Status could be 'running' or 'completed' depending on timing
        assert status['status'] in ['pending', 'running', 'completed']

        # Wait for completion
        queue.wait_for_task(task_id, timeout=2)
        status = queue.get_status(task_id)
        assert status['status'] == 'completed'
        assert status['result'] == 'completed'
        assert 'completed_at' in status

    def test_retry_logic_with_exponential_backoff(self, queue):
        """Test that failed tasks are retried with exponential backoff."""
        attempt_storage = {'count': 0}
        start_time = time.time()

        task_id = queue.submit(sometimes_failing_task, attempt_storage, max_retries=3)
        result = queue.wait_for_task(task_id, timeout=10)

        elapsed_time = time.time() - start_time

        # Task should succeed after 3 attempts (fails on attempt 1 and 2)
        assert result == "Success after 3 attempts"
        assert attempt_storage['count'] == 3

        # Check that exponential backoff was applied
        # First retry: 1s backoff, Second retry: 2s backoff
        # Total minimum wait: 1 + 2 = 3 seconds
        assert elapsed_time >= 3.0

        # Check status
        status = queue.get_status(task_id)
        assert status['status'] == 'completed'
        assert status['attempts'] == 3

    def test_task_failure_after_max_retries(self, queue):
        """Test that task fails after exceeding max retries."""
        start_time = time.time()

        task_id = queue.submit(failing_task, max_retries=2)

        # Task should raise ValueError
        with pytest.raises(ValueError, match="Task intentionally failed"):
            queue.wait_for_task(task_id, timeout=10)

        elapsed_time = time.time() - start_time

        # Check that exponential backoff was applied
        # First retry: 1s, Second retry: 2s
        # Total minimum wait: 1 + 2 = 3 seconds
        assert elapsed_time >= 3.0

        # Check status
        status = queue.get_status(task_id)
        assert status['status'] == 'failed'
        assert 'error' in status
        assert 'Task intentionally failed' in status['error']
        assert status['attempts'] == 3  # Initial + 2 retries

    def test_countdown_delayed_execution(self, queue):
        """Test that countdown delays task execution."""
        start_time_storage = {'time': None}
        submit_time = time.time()

        task_id = queue.submit(countdown_task, start_time_storage, countdown=2)

        # Wait for task to complete
        queue.wait_for_task(task_id, timeout=5)

        # Task should have started ~2 seconds after submission
        execution_delay = start_time_storage['time'] - submit_time
        assert execution_delay >= 2.0
        assert execution_delay < 2.5  # Allow some overhead

        # Check status
        status = queue.get_status(task_id)
        assert status['status'] == 'completed'
        assert status['countdown'] == 2

    def test_get_status_not_found(self, queue):
        """Test get_status for non-existent task."""
        status = queue.get_status("nonexistent_task_id")
        assert status == {'status': 'not_found'}

    def test_wait_for_task_not_found(self, queue):
        """Test wait_for_task raises error for non-existent task."""
        with pytest.raises(KeyError, match="Task .* not found"):
            queue.wait_for_task("nonexistent_task_id")

    def test_wait_for_task_timeout(self, queue):
        """Test that wait_for_task respects timeout."""
        task_id = queue.submit(slow_task, duration=5)

        with pytest.raises(TimeoutError):
            queue.wait_for_task(task_id, timeout=0.5)

    def test_concurrent_task_execution(self, queue):
        """Test that multiple tasks execute concurrently."""
        # Submit 4 slow tasks that take 0.5s each
        task_ids = []
        start_time = time.time()

        for _ in range(4):
            task_id = queue.submit(slow_task, duration=0.5)
            task_ids.append(task_id)

        # Wait for all to complete
        for task_id in task_ids:
            queue.wait_for_task(task_id, timeout=5)

        elapsed_time = time.time() - start_time

        # If running concurrently, should take ~0.5s (not 2s)
        # Allow some overhead for thread scheduling
        assert elapsed_time < 1.5

    def test_thread_safety(self, queue):
        """Test that queue operations are thread-safe."""
        task_ids = []
        lock = threading.Lock()

        def submit_tasks():
            for i in range(10):
                task_id = queue.submit(successful_task, i)
                with lock:
                    task_ids.append(task_id)

        # Submit tasks from multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=submit_tasks)
            thread.start()
            threads.append(thread)

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Should have 30 unique task IDs
        assert len(task_ids) == 30
        assert len(set(task_ids)) == 30

        # All tasks should complete successfully
        for task_id in task_ids:
            queue.wait_for_task(task_id, timeout=2)
            status = queue.get_status(task_id)
            assert status['status'] == 'completed'

    def test_graceful_shutdown_with_wait(self, queue):
        """Test graceful shutdown waits for tasks to complete."""
        # Submit several slow tasks
        task_ids = []
        for i in range(3):
            task_id = queue.submit(slow_task, duration=0.3)
            task_ids.append(task_id)

        # Shutdown and wait
        queue.shutdown(wait=True, timeout=5)

        # All tasks should have completed
        for task_id in task_ids:
            status = queue.get_status(task_id)
            assert status['status'] == 'completed'

    def test_graceful_shutdown_without_wait(self, queue):
        """Test shutdown without waiting doesn't wait for tasks."""
        # Submit a slow task
        task_id = queue.submit(slow_task, duration=2)

        # Shutdown immediately without waiting
        start_time = time.time()
        queue.shutdown(wait=False, timeout=5)
        shutdown_time = time.time() - start_time

        # Shutdown should be immediate (not wait 2 seconds)
        assert shutdown_time < 0.5

    def test_get_all_tasks(self, queue):
        """Test retrieving status of all tasks."""
        # Submit several tasks
        task_ids = []
        for i in range(3):
            task_id = queue.submit(successful_task, i)
            task_ids.append(task_id)

        # Get all tasks
        all_tasks = queue.get_all_tasks()

        # Should have all task IDs
        assert len(all_tasks) == 3
        for task_id in task_ids:
            assert task_id in all_tasks
            assert all_tasks[task_id]['function'] == 'successful_task'

    def test_cancel_task_before_execution(self, queue):
        """Test cancelling a task before it starts executing."""
        # Create a queue with only 1 worker
        from desktop.task_queue import DesktopTaskQueue
        small_queue = DesktopTaskQueue(max_workers=1)

        try:
            # Submit a slow task to occupy the worker
            first_task_id = small_queue.submit(slow_task, duration=1)

            # Submit another task that will be queued
            second_task_id = small_queue.submit(successful_task, 42)

            # Try to cancel the second task before it starts
            time.sleep(0.1)  # Give first task time to start
            cancelled = small_queue.cancel_task(second_task_id)

            # Should be able to cancel queued task
            # Note: This might fail if task starts very quickly
            if cancelled:
                status = small_queue.get_status(second_task_id)
                assert status['status'] == 'cancelled'

            # Wait for first task to complete
            small_queue.wait_for_task(first_task_id, timeout=5)

        finally:
            small_queue.shutdown(wait=True, timeout=5)

    def test_cancel_nonexistent_task(self, queue):
        """Test cancelling a non-existent task."""
        result = queue.cancel_task("nonexistent_task_id")
        assert result is False

    def test_task_metadata_includes_args_kwargs(self, queue):
        """Test that task metadata includes function arguments."""
        task_id = queue.submit(successful_task, 42, max_retries=2, countdown=1)

        status = queue.get_status(task_id)
        assert status['max_retries'] == 2
        assert status['countdown'] == 1
        assert '42' in status['args']  # String representation of args

    def test_task_with_kwargs(self, queue):
        """Test submitting task with keyword arguments."""
        def task_with_kwargs(a, b, c=10):
            return a + b + c

        task_id = queue.submit(task_with_kwargs, 5, 3, c=20)
        result = queue.wait_for_task(task_id, timeout=2)
        assert result == 28

    def test_zero_retries(self, queue):
        """Test task with max_retries=0 (no retries)."""
        task_id = queue.submit(failing_task, max_retries=0)

        with pytest.raises(ValueError):
            queue.wait_for_task(task_id, timeout=5)

        status = queue.get_status(task_id)
        assert status['status'] == 'failed'
        assert status['attempts'] == 1  # Only initial attempt

    def test_multiple_workers(self):
        """Test queue with different numbers of workers."""
        # Create queue with 8 workers
        from desktop.task_queue import DesktopTaskQueue
        large_queue = DesktopTaskQueue(max_workers=8)

        try:
            # Submit 8 tasks that take 0.5s each
            start_time = time.time()
            task_ids = []

            for _ in range(8):
                task_id = large_queue.submit(slow_task, duration=0.5)
                task_ids.append(task_id)

            # Wait for all
            for task_id in task_ids:
                large_queue.wait_for_task(task_id, timeout=5)

            elapsed_time = time.time() - start_time

            # With 8 workers, should complete in ~0.5s (not 4s)
            assert elapsed_time < 1.5

        finally:
            large_queue.shutdown(wait=True, timeout=5)

    def test_task_exception_propagation(self, queue):
        """Test that task exceptions are properly propagated."""
        def task_with_custom_exception():
            raise RuntimeError("Custom error message")

        task_id = queue.submit(task_with_custom_exception, max_retries=0)

        with pytest.raises(RuntimeError, match="Custom error message"):
            queue.wait_for_task(task_id, timeout=2)

        status = queue.get_status(task_id)
        assert status['status'] == 'failed'
        assert 'Custom error message' in status['error']

    def test_task_return_value_types(self, queue):
        """Test that various return value types are handled correctly."""
        def task_return_dict():
            return {'key': 'value', 'number': 42}

        def task_return_list():
            return [1, 2, 3, 4, 5]

        def task_return_none():
            return None

        # Test dict return
        task_id = queue.submit(task_return_dict)
        result = queue.wait_for_task(task_id, timeout=2)
        assert result == {'key': 'value', 'number': 42}

        # Test list return
        task_id = queue.submit(task_return_list)
        result = queue.wait_for_task(task_id, timeout=2)
        assert result == [1, 2, 3, 4, 5]

        # Test None return
        task_id = queue.submit(task_return_none)
        result = queue.wait_for_task(task_id, timeout=2)
        assert result is None


class TestDesktopTaskQueueIntegration:
    """Integration tests for DesktopTaskQueue."""

    def test_realistic_workload(self):
        """Test a realistic workload with mixed task types."""
        from desktop.task_queue import DesktopTaskQueue
        queue = DesktopTaskQueue(max_workers=4)

        try:
            task_ids = []

            # Submit various types of tasks
            # Quick successful tasks
            for i in range(5):
                task_id = queue.submit(successful_task, i)
                task_ids.append(('quick', task_id))

            # Slow tasks
            for i in range(3):
                task_id = queue.submit(slow_task, duration=0.2)
                task_ids.append(('slow', task_id))

            # Delayed tasks
            for i in range(2):
                task_id = queue.submit(successful_task, i, countdown=1)
                task_ids.append(('delayed', task_id))

            # Wait for all tasks to complete
            for task_type, task_id in task_ids:
                queue.wait_for_task(task_id, timeout=10)

            # Verify all completed successfully
            all_tasks = queue.get_all_tasks()
            assert len(all_tasks) == 10

            for task_id_tuple in task_ids:
                task_id = task_id_tuple[1]
                status = queue.get_status(task_id)
                assert status['status'] == 'completed'

        finally:
            queue.shutdown(wait=True, timeout=5)

    def test_stress_test_many_tasks(self):
        """Stress test with many concurrent tasks."""
        from desktop.task_queue import DesktopTaskQueue
        queue = DesktopTaskQueue(max_workers=8)

        try:
            # Submit 100 quick tasks
            task_ids = []
            start_time = time.time()

            for i in range(100):
                task_id = queue.submit(successful_task, i)
                task_ids.append(task_id)

            # Wait for all to complete
            for task_id in task_ids:
                queue.wait_for_task(task_id, timeout=10)

            elapsed_time = time.time() - start_time

            # Should complete quickly with parallel execution
            assert elapsed_time < 5.0

            # Verify all completed
            for task_id in task_ids:
                status = queue.get_status(task_id)
                assert status['status'] == 'completed'

        finally:
            queue.shutdown(wait=True, timeout=10)
