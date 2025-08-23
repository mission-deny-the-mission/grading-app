## Getting Started

This guide helps you install, configure, and run the Grading App locally.

### Prerequisites

- Python 3.10+
- Redis (for background task queue)

### 1) Set up the environment

```bash
python -m venv venv
source venv/bin/activate  # or: source venv/bin/activate.fish
pip install -r requirements.txt
cp env.example .env
```

Minimal `.env` (adjust as needed):

```env
OPENROUTER_API_KEY=
CLAUDE_API_KEY=
LM_STUDIO_URL=http://localhost:1234/v1
SECRET_KEY=change-me
DATABASE_URL=sqlite:///grading_app.db
```

### 2) Start dependencies

Redis must be running:

```bash
# Debian/Ubuntu
sudo apt-get install -y redis-server
sudo systemctl start redis

# macOS (Homebrew)
brew install redis
brew services start redis
```

### 3) Run the app

Option A: Full services (web + worker):

```bash
./start_services.sh
```

Option B: Basic (single-process):

```bash
python app.py
```

Visit `http://localhost:5000`.

### Providers and API keys

- OpenRouter, Claude API, and LM Studio are supported.
- Configure keys/URLs in the `.env` and in the app UI where applicable.

### Common issues

- Ensure Redis is running
- Verify API keys are set (cloud providers) or LM Studio is reachable
- Keep documents under the size limit configured in the app
