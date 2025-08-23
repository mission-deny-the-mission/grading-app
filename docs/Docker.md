## Docker (Optional)

### Quick start (production-like)

```bash
cp env.example .env
make build
make up
```

Apps:
- Web: http://localhost:5000
- Flower: http://localhost:5555

### Development with Docker Compose

```bash
make dev
make dev-worker   # Celery worker
make dev-beat     # Celery beat (optional)
```

Useful commands:

```bash
make dev-logs
make shell
make down
```
