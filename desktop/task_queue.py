"""
Desktop Task Queue Module

Provides a ThreadPoolExecutor-based task queue for async task processing
in a single-user desktop application. Replaces Celery/Redis for desktop deployment.

This implementation follows the specification in specs/004-desktop-app/research.md
section 2 (Async Task Processing Research).
"""

import concurrent.futures
from threading import Lock
from typing import Callable, Any, Optional, Dict
import time
import logging
import uuid

logger = logging.getLogger(__name__)


class DesktopTaskQueue:
    """
    A thread-based task queue manager for desktop applications.

    Features:
    - Thread pool for parallel task execution
    - Task tracking and status monitoring
    - Automatic retry with exponential backoff
    - Delayed task execution (countdown)
    - Thread-safe operations
    - Graceful shutdown
    """

    def __init__(self, max_workers: int = 4):
        """
        Initialize the task queue.

        Args:
            max_workers: Maximum number of worker threads (default: 4)
        """
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=max_workers)
        self.tasks: Dict[str, concurrent.futures.Future] = {}  # task_id -> Future
        self.task_metadata: Dict[str, Dict[str, Any]] = {}  # task_id -> metadata
        self.lock = Lock()
        self.next_task_id = 0
        logger.info(f"DesktopTaskQueue initialized with {max_workers} workers")

    def submit(self, func: Callable, *args, countdown: int = 0, max_retries: int = 3, **kwargs) -> str:
        """
        Submit a task to the queue.

        Args:
            func: The function to execute
            *args: Positional arguments for the function
            countdown: Delay before execution in seconds (default: 0)
            max_retries: Maximum retry attempts on failure (default: 3)
            **kwargs: Keyword arguments for the function

        Returns:
            str: Unique task ID for tracking

        Example:
            >>> task_id = queue.submit(process_job, job_id=123, countdown=5, max_retries=3)
            >>> status = queue.get_status(task_id)
        """
        with self.lock:
            task_id = str(self.next_task_id)
            self.next_task_id += 1

            # Initialize task metadata BEFORE submitting to executor
            # This prevents race condition where task completes before metadata exists
            self.task_metadata[task_id] = {
                'function': func.__name__,
                'status': 'pending',
                'submitted_at': time.time(),
                'countdown': countdown,
                'max_retries': max_retries,
                'args': str(args),  # Store string representation for debugging
                'kwargs': str(kwargs)
            }

        # Create wrapper with retry logic
        def task_wrapper():
            if countdown > 0:
                logger.debug(f"Task {task_id} waiting {countdown}s before execution")
                time.sleep(countdown)

            self._update_task_status(task_id, 'running', started_at=time.time())

            for attempt in range(max_retries + 1):
                try:
                    logger.debug(f"Task {task_id} executing (attempt {attempt + 1}/{max_retries + 1})")
                    result = func(*args, **kwargs)
                    self._update_task_status(
                        task_id,
                        'completed',
                        result=result,
                        completed_at=time.time(),
                        attempts=attempt + 1
                    )
                    logger.info(f"Task {task_id} completed successfully after {attempt + 1} attempt(s)")
                    return result
                except Exception as e:
                    if attempt < max_retries:
                        backoff = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s, 8s, ...
                        logger.warning(
                            f"Task {task_id} attempt {attempt + 1} failed: {e}. "
                            f"Retrying in {backoff}s"
                        )
                        time.sleep(backoff)
                    else:
                        logger.error(
                            f"Task {task_id} failed after {max_retries + 1} attempts: {e}"
                        )
                        self._update_task_status(
                            task_id,
                            'failed',
                            error=str(e),
                            failed_at=time.time(),
                            attempts=attempt + 1
                        )
                        raise

        # Submit to executor
        future = self.executor.submit(task_wrapper)

        with self.lock:
            self.tasks[task_id] = future

        logger.info(
            f"Task {task_id} submitted: {func.__name__} "
            f"(countdown={countdown}s, max_retries={max_retries})"
        )
        return task_id

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """
        Get the current status and result of a task.

        Args:
            task_id: The task ID returned by submit()

        Returns:
            dict: Task metadata including:
                - status: 'not_found', 'pending', 'running', 'completed', or 'failed'
                - function: Name of the function
                - submitted_at: Timestamp when task was submitted
                - result: Task result (if completed)
                - error: Error message (if failed)
                - attempts: Number of execution attempts

        Example:
            >>> status = queue.get_status(task_id)
            >>> if status['status'] == 'completed':
            ...     print(f"Result: {status['result']}")
        """
        with self.lock:
            if task_id not in self.tasks:
                return {'status': 'not_found'}
            return self.task_metadata[task_id].copy()

    def wait_for_task(self, task_id: str, timeout: Optional[float] = None) -> Optional[Any]:
        """
        Wait for a task to complete and return its result.

        Args:
            task_id: The task ID to wait for
            timeout: Maximum time to wait in seconds (None = wait forever)

        Returns:
            The task result if successful

        Raises:
            KeyError: If task_id not found
            concurrent.futures.TimeoutError: If timeout exceeded
            Exception: Any exception raised by the task

        Example:
            >>> task_id = queue.submit(slow_task)
            >>> result = queue.wait_for_task(task_id, timeout=30)
        """
        with self.lock:
            if task_id not in self.tasks:
                raise KeyError(f"Task {task_id} not found")
            future = self.tasks[task_id]

        return future.result(timeout=timeout)

    def _update_task_status(self, task_id: str, status: str, **kwargs):
        """
        Update task metadata (internal use).

        Args:
            task_id: The task ID to update
            status: New status value
            **kwargs: Additional metadata fields to update
        """
        with self.lock:
            if task_id in self.task_metadata:
                self.task_metadata[task_id]['status'] = status
                self.task_metadata[task_id].update(kwargs)

    def shutdown(self, wait: bool = True, timeout: int = 30):
        """
        Gracefully shut down the task queue.

        Args:
            wait: If True, wait for running tasks to complete
            timeout: Maximum time to wait for shutdown in seconds (only used if wait=True)

        Example:
            >>> queue.shutdown(wait=True, timeout=30)
        """
        logger.info("Shutting down task queue...")

        if wait:
            # Wait for running tasks with manual timeout handling
            # Note: ThreadPoolExecutor.shutdown() doesn't support timeout parameter directly
            start_time = time.time()

            # First, try to shutdown and wait for tasks
            self.executor.shutdown(wait=False, cancel_futures=False)

            # Wait for all futures to complete with timeout
            try:
                for task_id, future in list(self.tasks.items()):
                    remaining_time = timeout - (time.time() - start_time)
                    if remaining_time <= 0:
                        logger.warning(f"Task queue shutdown timeout after {timeout}s")
                        break
                    try:
                        future.result(timeout=remaining_time)
                    except Exception:
                        # Task may have failed, but we just want to ensure it's done
                        pass
                logger.info("Task queue shut down successfully (all tasks completed)")
            except Exception as e:
                logger.warning(f"Task queue shutdown encountered error: {e}")
        else:
            self.executor.shutdown(wait=False, cancel_futures=False)
            logger.info("Task queue shut down (tasks may still be running)")

    def get_all_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Get status of all tasks.

        Returns:
            dict: Mapping of task_id -> task metadata

        Example:
            >>> all_tasks = queue.get_all_tasks()
            >>> for task_id, metadata in all_tasks.items():
            ...     print(f"{task_id}: {metadata['status']}")
        """
        with self.lock:
            return {
                task_id: metadata.copy()
                for task_id, metadata in self.task_metadata.items()
            }

    def cancel_task(self, task_id: str) -> bool:
        """
        Attempt to cancel a pending or running task.

        Args:
            task_id: The task ID to cancel

        Returns:
            bool: True if cancellation was successful, False otherwise

        Note:
            Tasks that have already started may not be cancellable.

        Example:
            >>> task_id = queue.submit(long_task)
            >>> success = queue.cancel_task(task_id)
        """
        with self.lock:
            if task_id not in self.tasks:
                logger.warning(f"Cannot cancel task {task_id}: not found")
                return False

            future = self.tasks[task_id]

        cancelled = future.cancel()

        if cancelled:
            self._update_task_status(task_id, 'cancelled', cancelled_at=time.time())
            logger.info(f"Task {task_id} cancelled successfully")
        else:
            logger.warning(f"Task {task_id} could not be cancelled (already running or completed)")

        return cancelled


# Global instance for application-wide use
task_queue = DesktopTaskQueue(max_workers=4)
