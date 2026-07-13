# AI Code Security Scanner

Find and fix OWASP Top 10 vulnerabilities with AI-powered plain-English explanations and one-click code fixes.

## Stack
- **Frontend**: Next.js 15, Tailwind CSS, CodeMirror 6
- **Backend**: FastAPI, SQLAlchemy 2.0 async, Alembic
- **AI**: Groq Llama 3.3 70B
- **Data**: PostgreSQL 16, Redis 7
- **DevOps**: Docker Compose, GitHub Actions

## Quick Start

```bash
# 1. Clone and set up environment
git clone <repo>
cd ai-code-scanner
make setup         # copies .env.example → .env

# 2. Fill in your secrets in .env
#    Required: GROQ_API_KEY, JWT_SECRET
nano .env

# 3. Start everything
make dev

# 4. Run migrations (in a second terminal)
make migrate

# App is live at:
#   Frontend: http://localhost:3000
#   Backend:  http://localhost:8000
#   API docs: http://localhost:8000/docs
```

## Commands

| Command | Description |
|---|---|
| `make dev` | Start all services with hot-reload |
| `make stop` | Stop all services |
| `make migrate` | Apply database migrations |
| `make migrate-create msg="..."` | Create a new migration |
| `make test` | Run all tests |
| `make lint` | Lint all code |
| `make format` | Auto-format all code |
| `make logs` | Tail all service logs |
| `make shell-backend` | Shell into backend container |
| `make db-shell` | Open psql |
| `make clean` | Remove containers and volumes |

## Project Structure

```
ai-code-scanner/
├── backend/
│   ├── app/
│   │   ├── api/v1/routes/     # auth, scans, github, health
│   │   ├── core/              # config, db, redis, security, middleware
│   │   ├── models/            # SQLAlchemy models
│   │   ├── schemas/           # Pydantic schemas
│   │   └── services/
│   │       ├── scanner/       # chunker, ai_client, prompts, language_detector
│   │       └── github/        # github_client
│   ├── tests/
│   └── alembic/
├── frontend/
│   └── src/
│       ├── app/               # Next.js pages
│       ├── components/        # FindingCard, SeveritySummary, ScanProgress
│       ├── lib/               # api client, severity utils
│       └── types/
└── docker/
    └── postgres/init.sql
```

## GitHub App Setup

1. Go to https://github.com/settings/apps/new
2. Set webhook URL to `https://your-domain.com/api/v1/github/webhook`
3. Permissions: Pull requests (Read & Write), Contents (Read)
4. Events: Pull request
5. Download the private key and add to `.env`

## Environment Variables

See `.env.example` for all required variables with descriptions.
