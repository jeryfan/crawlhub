# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Full-stack application template with FastAPI backend and Next.js frontends. The project consists of three main parts:
- `app/` - FastAPI backend API server
- `web/` - Next.js user-facing frontend
- `admin/` - Next.js admin dashboard frontend

## Common Commands

### Backend (app/)

```bash
cd app

# Install dependencies (uses uv package manager)
uv sync

# Linting (uses ruff)
uv run ruff check .
uv run ruff format .
```

### Frontend (web/ and admin/)

```bash
cd web  # or cd admin

# Install dependencies
pnpm install

# Run development server (port 3000 for web, different for admin)
pnpm dev

# Build for production
pnpm build

# Run linting
pnpm lint
pnpm lint:fix

# Type checking
pnpm type-check

# Run tests
pnpm test
pnpm test:watch

# Check i18n
pnpm check-i18n
```

### Docker

Backend development, testing, and migrations must be executed inside Docker containers:

```bash
cd docker

# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d app

# View logs
docker-compose logs -f app

# Run commands inside container (preferred for development)
docker exec app uv run pytest                                    # Run tests
docker exec app uv run alembic upgrade head                      # Apply migrations
docker exec app uv run alembic revision --autogenerate -m "update billing"  # Create migration
```

## Architecture

### Backend (app/)

The FastAPI backend follows a layered architecture:

- **app_factory.py** - Application factory pattern with lifespan management and extension initialization
- **app.py** - Entry point that creates the app and exposes Celery instance
- **routers/** - API route handlers organized by domain (console/, admin/, files/)
- **services/** - Business logic layer (account_service.py, billing_service.py, etc.)
- **models/** - SQLAlchemy async ORM models (account.py, user.py, billing.py, etc.)
- **schemas/** - Pydantic request/response schemas
- **core/** - Core utilities (database.py, file handling, RAG extractors)
- **extensions/** - Pluggable extensions (storage, celery, redis, mail, elasticsearch)
- **configs/** - Configuration using pydantic-settings, composed from multiple config classes
- **tasks/** - Celery async tasks (mail tasks, document processing, billing)
- **dependencies/** - FastAPI dependency injection
- **middlewares/** - Custom middleware

Key patterns:
- Async SQLAlchemy with PostgreSQL/MySQL support
- Extension system: each extension in `extensions/` has `init_app()` and optional `is_enabled()`
- Configuration via `.env` file, loaded through `configs/__init__.py`
- Multi-tenant architecture with workspaces and accounts
- **API response format**: All endpoints must return unified format:
  ```json
  {"code": 200, "msg": "success", "data": {...}}
  ```

### Frontend (web/ and admin/)

Next.js 15 with App Router:

- **app/** - Next.js app directory with route handlers
- **components/** - Reusable React components
- **context/** - React context providers
- **hooks/** - Custom React hooks
- **service/** - API client services
- **i18n-config/** - Internationalization configuration
- **utils/** - Utility functions
- **types/** - TypeScript type definitions

Key technologies: React 19, TypeScript, Tailwind CSS, Zustand, React Query, i18next

## Configuration

Backend configuration is composed from multiple sources in `app/configs/`:
- CommonConfig, DeploymentConfig, FeatureConfig, MiddlewareConfig, PaymentConfig
- All merged into `AppConfig` and instantiated as `app_config`

Copy `.env.example` to `.env` in both `app/` and `docker/` directories.

## Testing

Backend uses pytest with async support:
- Test markers: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.slow`
- Fixtures defined in `conftest.py`
- Coverage reports generated automatically

Frontend uses Jest with React Testing Library.

## 完成修改后请勿提交代码
