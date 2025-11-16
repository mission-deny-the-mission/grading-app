# Python Module Interfaces

**Feature**: 004-desktop-app
**Date**: 2025-11-16
**Version**: 1.0.0

## Overview

This document defines the Python API contracts for desktop-specific modules. These are internal interfaces between components, not HTTP APIs.

---

## Module: `desktop/credentials.py`

**Purpose**: Manage AI provider API keys using OS credential storage

### Functions

#### `initialize_keyring() -> None`

Initialize keyring backend, fallback to encrypted file if OS backend unavailable.

**Signature**:
```python
def initialize_keyring() -> None:
    """
    Initialize keyring backend.

    Automatically selects best available backend:
    1. OS-native (Windows Credential Manager, macOS Keychain, Linux Secret Service)
    2. keyrings.cryptfile (encrypted file with master password)
    3. Fail backend (raises error)

    Raises:
        RuntimeError: If no suitable backend available
    """
```

**Side Effects**:
- Sets global keyring backend
- May prompt user for master password (if using keyrings.cryptfile)
- Logs backend selection

**Error Handling**:
- Raises `RuntimeError` if all backends fail

---

#### `set_api_key(provider_key: str, api_key: str) -> bool`

Store API key in OS credential manager.

**Signature**:
```python
def set_api_key(provider_key: str, api_key: str) -> bool:
    """
    Store API key in OS credential manager.

    Args:
        provider_key: Provider identifier (e.g., "openrouter_api_key")
        api_key: API key value (may be empty string to clear)

    Returns:
        True if successful, False otherwise

    Raises:
        ValueError: If provider_key not in PROVIDERS list
    """
```

**Validation**:
- `provider_key` must be in `PROVIDERS` constant list
- `api_key` may be any string (including empty)
- **Does NOT validate API key format** (caller's responsibility)

**Side Effects**:
- Writes to OS credential manager
- Logs success/failure (does NOT log key value)

**Error Handling**:
- Returns `False` on keyring write failure
- Raises `ValueError` for invalid `provider_key`

---

#### `get_api_key(provider_key: str) -> str`

Retrieve API key from OS credential manager.

**Signature**:
```python
def get_api_key(provider_key: str) -> str:
    """
    Retrieve API key from OS credential manager.

    Args:
        provider_key: Provider identifier (e.g., "openrouter_api_key")

    Returns:
        API key value or empty string if not found

    Raises:
        ValueError: If provider_key not in PROVIDERS list
    """
```

**Return Values**:
- Non-empty string: API key retrieved successfully
- Empty string: No key stored for this provider, or key was explicitly set to empty

**Error Handling**:
- Returns empty string on keyring read failure (logs error)
- Raises `ValueError` for invalid `provider_key`

---

#### `delete_api_key(provider_key: str) -> bool`

Delete API key from OS credential manager.

**Signature**:
```python
def delete_api_key(provider_key: str) -> bool:
    """
    Delete API key from OS credential manager.

    Args:
        provider_key: Provider identifier (e.g., "openrouter_api_key")

    Returns:
        True if successful (or key didn't exist), False on error

    Raises:
        ValueError: If provider_key not in PROVIDERS list
    """
```

**Behavior**:
- Idempotent: Deleting non-existent key returns `True`
- Logs deletion

**Error Handling**:
- Returns `False` on keyring delete failure
- Raises `ValueError` for invalid `provider_key`

---

### Constants

```python
SERVICE_NAME: str = "grading-app"  # Used for all keyring entries

PROVIDERS: List[str] = [
    "openrouter_api_key",
    "claude_api_key",
    "openai_api_key",
    "gemini_api_key",
    "nanogpt_api_key",
    "chutes_api_key",
    "zai_api_key",
]
```

---

## Module: `desktop/task_queue.py`

**Purpose**: Async task processing using ThreadPoolExecutor

### Class: `DesktopTaskQueue`

Thread-safe task queue with retry logic and graceful shutdown.

#### `__init__(max_workers: int = 4)`

**Signature**:
```python
def __init__(self, max_workers: int = 4) -> None:
    """
    Initialize task queue.

    Args:
        max_workers: Number of worker threads (default: 4)
    """
```

**State Initialization**:
- Creates `ThreadPoolExecutor` with `max_workers` threads
- Initializes task registry and metadata dictionaries
- Sets up thread lock for concurrency safety

---

#### `submit(func, *args, countdown=0, max_retries=3, **kwargs) -> str`

Submit task to queue.

**Signature**:
```python
def submit(
    self,
    func: Callable,
    *args: Any,
    countdown: int = 0,
    max_retries: int = 3,
    **kwargs: Any
) -> str:
    """
    Submit task to queue.

    Args:
        func: Task function to execute
        countdown: Delay before execution (seconds)
        max_retries: Maximum retry attempts on failure
        *args, **kwargs: Task function arguments

    Returns:
        Task ID (string) for tracking

    Raises:
        TypeError: If func is not callable
    """
```

**Behavior**:
- Assigns unique task ID
- Wraps task with retry logic (exponential backoff: 1s, 2s, 4s, ...)
- Submits to thread pool
- Returns immediately (non-blocking)

**Retry Logic**:
- On failure, waits `2^attempt` seconds before retrying
- Logs each retry attempt
- After max_retries exhausted, marks task as failed

**Thread Safety**: All operations use internal lock

---

#### `get_status(task_id: str) -> dict`

Get task status and metadata.

**Signature**:
```python
def get_status(self, task_id: str) -> dict:
    """
    Get task status and result.

    Args:
        task_id: Task ID returned from submit()

    Returns:
        dict with keys:
            - status: 'pending' | 'completed' | 'failed' | 'not_found'
            - function: Task function name
            - submitted_at: Unix timestamp
            - countdown: Configured delay
            - max_retries: Configured max retries
            - result: Task return value (if completed)
            - error: Error message (if failed)
    """
```

**Status Values**:
- `pending`: Task submitted, not yet completed
- `completed`: Task finished successfully, `result` field present
- `failed`: Task failed after all retries, `error` field present
- `not_found`: Task ID not recognized

**Thread Safety**: Returns copy of metadata (safe to inspect)

---

#### `shutdown(wait=True, timeout=30)`

Gracefully shut down task queue.

**Signature**:
```python
def shutdown(self, wait: bool = True, timeout: int = 30) -> None:
    """
    Gracefully shut down task queue.

    Args:
        wait: If True, wait for running tasks to complete
        timeout: Maximum seconds to wait (if wait=True)

    Raises:
        TimeoutError: If tasks don't complete within timeout
    """
```

**Behavior**:
- If `wait=True`: Blocks until all running tasks complete or timeout
- If `wait=False`: Cancels pending tasks immediately
- Cleans up thread pool resources

**Use Case**: Called on application exit

---

### Global Instance

```python
task_queue: DesktopTaskQueue = DesktopTaskQueue(max_workers=4)
```

**Usage Pattern**:
```python
from desktop.task_queue import task_queue

# Submit task
task_id = task_queue.submit(process_job, job_id=123)

# Check status later
status = task_queue.get_status(task_id)
if status['status'] == 'completed':
    result = status['result']
```

---

## Module: `desktop/updater.py`

**Purpose**: Auto-update mechanism using tufup

### Class: `DesktopUpdater`

#### `__init__(app_name, current_version, update_url)`

**Signature**:
```python
def __init__(
    self,
    app_name: str,
    current_version: str,
    update_url: str
) -> None:
    """
    Initialize updater client.

    Args:
        app_name: Application name for update identification
        current_version: Current version (semver string)
        update_url: Base URL for update server

    Raises:
        ValueError: If current_version not valid semver
    """
```

**Validation**:
- `current_version` must be valid semver (e.g., "1.0.0")
- `update_url` must be valid HTTP/HTTPS URL

---

#### `check_for_updates() -> dict`

Check if updates are available.

**Signature**:
```python
def check_for_updates(self) -> dict:
    """
    Check if updates are available.

    Returns:
        dict with keys:
            - available: bool
            - version: str (new version, if available)
            - current: str (current version)
            - url: str (release URL, if available)
            - error: str (error message, if check failed)

    Raises:
        None (errors returned in dict['error'])
    """
```

**Network Requirements**:
- Requires internet connectivity
- Timeout: 30 seconds
- Retries: 3 attempts with exponential backoff

**Caching**:
- Results cached for 24 hours
- Cache invalidated on new check request

---

#### `download_update(progress_callback=None) -> bool`

Download update package.

**Signature**:
```python
def download_update(
    self,
    progress_callback: Optional[Callable[[int, int], None]] = None
) -> bool:
    """
    Download update package.

    Args:
        progress_callback: Optional callback(bytes_downloaded, total_bytes)

    Returns:
        True if download successful, False otherwise
    """
```

**Progress Callback**:
```python
def on_progress(bytes_downloaded: int, total_bytes: int):
    percent = (bytes_downloaded / total_bytes) * 100
    print(f"Download: {percent:.1f}%")
```

**Verification**:
- Verifies TUF signature
- Validates SHA256 checksum
- Rejects if verification fails

---

#### `apply_update() -> None`

Apply downloaded update (restarts application).

**Signature**:
```python
def apply_update(self) -> None:
    """
    Apply downloaded update.

    This function DOES NOT RETURN (restarts application).

    Raises:
        RuntimeError: If no update downloaded
        OSError: If update application fails
    """
```

**Behavior**:
- Backs up current version
- Replaces executables with new version
- Restarts application using `os.execl()`
- **This function does not return** (process is replaced)

**Pre-Conditions**:
- Update must be downloaded first (`download_update()` returned `True`)

---

## Module: `desktop/app_wrapper.py`

**Purpose**: Flask application lifecycle management

### Functions

#### `configure_app_for_desktop(app) -> Flask`

Configure Flask app for desktop deployment.

**Signature**:
```python
def configure_app_for_desktop(app: Flask) -> Flask:
    """
    Configure Flask app for desktop deployment.

    Args:
        app: Flask application instance

    Returns:
        Configured Flask app

    Side Effects:
        - Initializes keyring
        - Loads API keys from OS credential manager into environment
        - Configures SQLite database path
        - Creates user data directories
    """
```

**Configuration Changes**:
1. Database: SQLite in user data directory (not PostgreSQL)
2. Uploads: User data directory (not ./uploads)
3. API Keys: Loaded from OS credential manager
4. Logs: User data directory

---

#### `get_user_data_dir() -> Path`

Get platform-specific user data directory.

**Signature**:
```python
def get_user_data_dir() -> Path:
    """
    Get platform-specific user data directory.

    Returns:
        Path to user data directory (created if doesn't exist)

    Platform paths:
        - Windows: %APPDATA%\\GradingApp
        - macOS: ~/Library/Application Support/GradingApp
        - Linux: ~/.local/share/GradingApp
    """
```

**Behavior**:
- Creates directory if it doesn't exist
- Sets appropriate permissions (user-only read/write)
- Returns `pathlib.Path` object

---

#### `start_flask_server(app, port=None) -> int`

Start Flask server in background thread.

**Signature**:
```python
def start_flask_server(app: Flask, port: Optional[int] = None) -> int:
    """
    Start Flask server in background thread.

    Args:
        app: Flask application instance
        port: Port number (None = auto-select)

    Returns:
        Port number server is listening on

    Raises:
        OSError: If port binding fails
    """
```

**Behavior**:
- Auto-selects available port if `port=None`
- Starts server in daemon thread
- Waits for server to be ready (max 10 seconds)
- Returns actual port number

**Thread Safety**: Server runs in separate daemon thread

---

## Module: `desktop/window_manager.py`

**Purpose**: Desktop window and system tray management

### Functions

#### `create_main_window(url, title="Grading App") -> None`

Create and show main application window.

**Signature**:
```python
def create_main_window(url: str, title: str = "Grading App") -> None:
    """
    Create and show main application window.

    Args:
        url: Flask server URL (e.g., "http://127.0.0.1:5050")
        title: Window title

    This function BLOCKS until window is closed.
    """
```

**Behavior**:
- Creates PyWebView window
- Loads Flask URL
- Shows loading screen until page loads
- **Blocks** until user closes window

**Window Configuration**:
- Size: 1280x800 (or last saved geometry from settings)
- Resizable: Yes
- Min size: 800x600

---

#### `create_system_tray(on_show, on_hide, on_quit) -> None`

Create system tray icon with menu.

**Signature**:
```python
def create_system_tray(
    on_show: Callable[[], None],
    on_hide: Callable[[], None],
    on_quit: Callable[[], None]
) -> None:
    """
    Create system tray icon with menu.

    Args:
        on_show: Callback when "Show" clicked
        on_hide: Callback when "Hide" clicked
        on_quit: Callback when "Quit" clicked

    Runs in separate thread (non-blocking).
    """
```

**Menu Items**:
- Show Window
- Hide Window
- Check for Updates
- Settings
- Quit

**Platform Notes**:
- Windows: Icon in system tray
- macOS: Icon in menu bar
- Linux: Icon in system tray (if supported by desktop environment)

---

## Error Handling Policy

### All Modules

**Logging**:
- Use Python `logging` module
- Log levels:
  - **DEBUG**: Function entry/exit, detailed progress
  - **INFO**: Normal operations (key stored, update available)
  - **WARNING**: Recoverable errors (keyring fallback, update check failed)
  - **ERROR**: Operation failures requiring attention
  - **CRITICAL**: Fatal errors preventing application startup

**Exception Handling**:
- **Public functions**: Catch exceptions, return error values (False, empty string, error dict)
- **Private functions**: May raise exceptions (caught by public functions)
- **Never**: Catch `KeyboardInterrupt` or `SystemExit`

**Security**:
- **Never log API key values** (even in DEBUG mode)
- Mask sensitive data: `"Stored key ***ABCD"` (last 4 characters only)

---

## Thread Safety Guarantees

| Module | Thread Safety |
|--------|--------------|
| `credentials.py` | ✅ All functions thread-safe (`keyring` library handles locking) |
| `task_queue.py` | ✅ All operations protected by internal lock |
| `updater.py` | ⚠️ Not thread-safe (call from main thread only) |
| `app_wrapper.py` | ✅ All functions thread-safe |
| `window_manager.py` | ⚠️ Call from main thread (UI operations not thread-safe) |

---

## Testing Contracts

### Mock Interfaces

**For Unit Tests**:

```python
# Mock keyring
from unittest.mock import MagicMock
import keyring

keyring.get_keyring = MagicMock(return_value=FakeKeyring())

# Mock task queue
from desktop.task_queue import DesktopTaskQueue

queue = DesktopTaskQueue(max_workers=1)  # Single worker for deterministic tests
```

**Integration Test Requirements**:
- OS credential manager available (or skip test on unsupported platforms)
- Network access for update tests (or mock HTTP responses)
- Display server for window manager tests (or use headless mode)

---

**Document Status**: ✅ **Complete**
**Version**: 1.0.0
**Next Review**: After implementation, before release
