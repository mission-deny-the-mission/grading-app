"""
Loading screen component for desktop application startup.

Displays a loading/splash screen while Flask server initializes
and database migrations run.
"""

import time
import threading
from pathlib import Path


class LoadingScreen:
    """
    Simple loading screen that can be shown during app startup.

    This is a placeholder for PyWebView integration - in production,
    this would display an actual splash screen window.
    """

    def __init__(self, title="Grading App - Starting", message="Initializing..."):
        """Initialize the loading screen."""
        self.title = title
        self.message = message
        self.window = None
        self.is_visible = False

    def show(self):
        """Display the loading screen."""
        self.is_visible = True
        print(f"\n{'='*60}")
        print(f"  {self.title}")
        print(f"{'='*60}")
        self._update_progress()

    def update_message(self, message):
        """Update the loading message."""
        self.message = message
        print(f"  → {message}")

    def _update_progress(self):
        """Show loading progress."""
        stages = [
            "Configuring Flask app...",
            "Initializing database...",
            "Starting periodic scheduler...",
            "Allocating port...",
            "Starting Flask server...",
            "Launching window...",
        ]

        for stage in stages:
            self.update_message(stage)
            time.sleep(0.1)  # Simulate work

    def hide(self):
        """Hide the loading screen."""
        self.is_visible = False
        print(f"{'='*60}\n")

    def __enter__(self):
        """Context manager entry."""
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.hide()


class PyWebViewLoadingScreen(LoadingScreen):
    """
    PyWebView-based loading screen (for GUI mode).

    This creates an actual window for the loading screen if pywebview
    is available and the desktop app is running in GUI mode.
    """

    def __init__(self, title="Grading App - Starting", message="Initializing..."):
        """Initialize PyWebView loading screen."""
        super().__init__(title, message)
        self.html_content = self._create_html()

    def _create_html(self):
        """Create HTML for the loading screen."""
        return """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Grading App</title>
            <style>
                * {
                    margin: 0;
                    padding: 0;
                    box-sizing: border-box;
                }

                body {
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                }

                .container {
                    text-align: center;
                    color: white;
                }

                .logo {
                    font-size: 48px;
                    margin-bottom: 20px;
                    font-weight: bold;
                }

                .title {
                    font-size: 28px;
                    margin-bottom: 10px;
                    font-weight: 600;
                }

                .subtitle {
                    font-size: 14px;
                    opacity: 0.9;
                    margin-bottom: 40px;
                }

                .spinner {
                    width: 40px;
                    height: 40px;
                    border: 4px solid rgba(255, 255, 255, 0.3);
                    border-top: 4px solid white;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                    margin: 0 auto 30px;
                }

                @keyframes spin {
                    0% { transform: rotate(0deg); }
                    100% { transform: rotate(360deg); }
                }

                .status {
                    font-size: 12px;
                    opacity: 0.8;
                    margin-top: 20px;
                }

                .dot {
                    display: inline-block;
                    width: 3px;
                    height: 3px;
                    background: white;
                    border-radius: 50%;
                    margin: 0 2px;
                    animation: blink 1.4s infinite;
                }

                .dot:nth-child(2) {
                    animation-delay: 0.2s;
                }

                .dot:nth-child(3) {
                    animation-delay: 0.4s;
                }

                @keyframes blink {
                    0%, 60%, 100% { opacity: 0.3; }
                    30% { opacity: 1; }
                }
            </style>
        </head>
        <body>
            <div class="container">
                <div class="logo">📚</div>
                <div class="title">Grading App</div>
                <div class="subtitle">Desktop Application</div>
                <div class="spinner"></div>
                <div class="status">
                    Initializing
                    <span class="dot"></span>
                    <span class="dot"></span>
                    <span class="dot"></span>
                </div>
            </div>
        </body>
        </html>
        """

    def show(self):
        """Display the PyWebView loading screen."""
        super().show()

        try:
            import webview

            self.window = webview.create_window(
                title=self.title,
                html=self.html_content,
                width=400,
                height=500
            )

            # Start window in background thread
            def run_window():
                webview.start()

            window_thread = threading.Thread(target=run_window, daemon=True)
            window_thread.start()

            # Give window time to render
            time.sleep(0.5)

        except ImportError:
            print("  Note: PyWebView not available, showing text loading screen")
            pass

    def hide(self):
        """Hide the PyWebView loading screen."""
        super().hide()

        try:
            if self.window:
                # Note: PyWebView window close is handled by desktop/main.py
                pass
        except Exception:
            pass


def show_loading_screen():
    """
    Show a loading screen during app startup.

    Usage:
        with show_loading_screen() as loader:
            loader.update_message("Starting database...")
            # ... perform startup operations ...
    """
    try:
        import webview
        return PyWebViewLoadingScreen()
    except ImportError:
        return LoadingScreen()
