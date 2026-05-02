# AI Code Reviewer

Production-grade AI code review bot built as a GitHub App. It listens for pull request webhooks, analyzes diffs with Claude + Semgrep, and posts intelligent inline review comments.

## Stack

- Python 3.11+
- FastAPI
- SQLAlchemy 2.0 async + Postgres
- Redis RQ worker queue
- Anthropic Claude API
- Semgrep SAST

## Project Layout

See `app/` for API, webhook handling, GitHub integration, review engine, and persistence modules.

## Quick Start

1. Copy `.env.example` to `.env` and fill all secrets.
2. Build and start services:
   ```bash
   docker compose up --build
   ```
3. Run tests:
   ```bash
   pytest -q
   ```

## GitHub App Setup

1. Use `.github/app-manifest.json` as the app manifest.
2. Set webhook URL to your deployed `/webhook` endpoint.
3. Install the app on your repositories.

## Webhook Flow

1. `POST /webhook` verifies HMAC signature.
2. Pull request events (`opened`, `reopened`, `synchronize`) are accepted.
3. Review job is queued in Redis RQ.
4. Worker fetches PR diff, runs AI + Semgrep analysis, persists results, posts PR review comments.

## Security Notes

- No secrets are hardcoded.
- All secrets/config values are environment-driven.
- GitHub signatures are verified with HMAC-SHA256.

