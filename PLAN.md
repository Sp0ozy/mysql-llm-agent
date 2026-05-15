# PLAN.md — Task B: Dockerize the MySQL LLM Agent

> Previous Task B (visualization agent) is complete and shipped. This file now tracks the new Task B: containerizing the existing process with Docker Compose. Visualization-agent plan archived in git history.

## Context

The repo currently ships two CLI workflows on `main`:

- `main.py` — interactive Q&A loop (Task A, complete, tagged `gemini-qa-v1`)
- `generate_report.py` — one-shot HTML report (visualization agent, complete)

Both share `src/` modules, the same Python deps, and the same `.env`-driven config (DB credentials + `GEMINI_API_KEY`). The MySQL database is **remote** (`87.110.123.151`); no local DB is needed in the stack.

This task requires the project to run inside Docker Compose with: a pinned list of components/versions, a single `docker-compose.yaml`, and accessible logs. Plus an optional GitHub-side hook for tests/checks.

**User decisions (confirmed):**

1. **Stack scope** — CLI only. One Python service that can run either script. UI from the `app` branch is deferred.
2. **Logs** — stdout only; viewed via `docker compose logs -f`. No code changes (existing `print()` calls already write to stdout).
3. **GitHub CI** — minimal `.github/workflows/ci.yml` that builds the image and runs an import-only smoke test (no DB / no API key required).
4. **Report output** — bind-mount `./output` to host; user opens `output/report.html` in the host browser.

**Goal**: a grader can `cp .env.example .env`, fill in credentials, and run `docker compose run --rm app python generate_report.py` (or `python main.py` for interactive Q&A) without installing Python or any deps locally.

---

## Components and versions to pin

These go in the deliverable and the Dockerfile / compose file:

| Component | Version | Why pinned |
| --- | --- | --- |
| Python base image | `python:3.11-slim` | Project requires 3.11+; slim keeps image small |
| Docker Compose schema | v2 (no top-level `version:` key) | Compose v2 is current; v1 is EOL |
| `sqlalchemy` | `>=2.0.0` | per `requirements.txt` |
| `pymysql` | `>=1.1.0` | per `requirements.txt` |
| `google-genai` | `>=1.0.0` | per `requirements.txt` |
| `python-dotenv` | `>=1.0.0` | per `requirements.txt` |
| `pandas` | `>=2.0.0` | per `requirements.txt` |
| `matplotlib` | `>=3.8.0` | per `requirements.txt` |
| `jinja2` | `>=3.1.0` | per `requirements.txt` |

**Gemini model chain** (already in `src/llm_client.py`; documented for the deliverable):

1. `gemini-2.5-flash` (primary)
2. `gemini-2.0-flash` (fallback on 503 / 429)
3. `gemini-1.5-flash` (final fallback)

---

## Files to CREATE

| File | Purpose |
| --- | --- |
| `Dockerfile` | Build the runtime image |
| `.dockerignore` | Keep build context small / no secrets |
| `docker-compose.yaml` | Single `app` service for both CLI scripts |
| `.github/workflows/ci.yml` | CI: build image + import smoke test |

## Files to MODIFY

| File | Change |
| --- | --- |
| `README.md` | Append "Run with Docker" section + components/versions table |

## Files to LEAVE UNTOUCHED

- `main.py`, `generate_report.py`, `src/**` — run as-is inside the container
- `requirements.txt` — already correct; Dockerfile installs from it
- `.env.example` — already lists exactly the vars the container needs
- `.gitignore` — already excludes `.env`, `output/`, `__pycache__/`

---

## Build Order (strict — stop after each step, verify, then continue)

### Step 1 — `.dockerignore`

Exclude from build context so subsequent builds don't ship `venv/` or `.env`:
`.git`, `venv/`, `__pycache__/`, `*.pyc`, `output/`, `.env`, `.claude/`, `app/`.

**Verify:** file exists with the above entries.

---

### Step 2 — `Dockerfile`

Single-stage, `python:3.11-slim` base.

- `WORKDIR /app`
- Copy `requirements.txt` first (layer cache) → `pip install --no-cache-dir -r requirements.txt`
- Copy the rest of the repo
- `ENV PYTHONUNBUFFERED=1` — critical so `print()` flushes to `docker compose logs` immediately
- `ENV PYTHONDONTWRITEBYTECODE=1` — no `.pyc` clutter
- No default `CMD`; the user picks `python main.py` or `python generate_report.py` at runtime

**Verify:**
```bash
docker build -t mysql-llm-agent:dev .
docker run --rm mysql-llm-agent:dev python -c "import src.planner, src.visualizer, src.report; print('ok')"
```

---

### Step 3 — `docker-compose.yaml`

One service, `app`:

- `build: .`
- `image: mysql-llm-agent:latest`
- `env_file: .env` — loads DB creds + `GEMINI_API_KEY`
- `volumes:` `./output:/app/output` — report HTML lands on host
- `stdin_open: true` and `tty: true` — required for the interactive `input()` in `main.py`
- No `command:` (caller supplies it)
- No port mapping (CLI only)
- No restart policy (one-shot runs)

**Verify:**
```bash
docker compose config            # parses cleanly
docker compose build
```

---

### Step 4 — Smoke test report mode

```bash
docker compose run --rm app python generate_report.py
```

Confirm `output/report.html` appears on the host with charts and insights.

---

### Step 5 — Smoke test Q&A mode

```bash
docker compose run --rm app python main.py
```

Type one question, see SQL + answer, type `exit`. Confirms `stdin_open` + `tty` work.

---

### Step 6 — Verify logs

In one terminal run the report; in another:
```bash
docker compose logs -f app
```
The `[1/5] …` progress prints should appear in real time. Confirms `PYTHONUNBUFFERED=1`.

---

### Step 7 — `.github/workflows/ci.yml`

Triggers: `push` to `main`, `pull_request`. Steps:

- `actions/checkout@v4`
- `docker/setup-buildx-action@v3`
- `docker build -t mysql-llm-agent:ci .`
- Smoke check inside the freshly built image:
  ```sh
  docker run --rm mysql-llm-agent:ci python -c "import src.db_introspect, src.context_builder, src.llm_client, src.pipeline, src.planner, src.visualizer, src.report; print('imports OK')"
  ```

Verifies image builds, deps install, modules import cleanly — without DB or `GEMINI_API_KEY`.

**Verify:** push, watch Actions tab go green.

---

### Step 8 — README update

Append a "Run with Docker" section with the three commands a grader needs:

```bash
cp .env.example .env
docker compose build
docker compose run --rm app python generate_report.py   # report mode
docker compose run --rm app python main.py              # Q&A mode
docker compose logs -f app                               # logs
```

Also include the pinned versions table so the grader can see "required models and versions."

---

### Step 9 — Commit + tag

- `git add -A && git commit -m "feat: dockerize CLI workflows with compose + CI"`
- Tag (e.g. `task-b-docker`) so the grader can check out the exact state.
- Push.

---

## What NOT to do

- Don't add a MySQL service to compose — the DB is remote by design.
- Don't bake `.env` into the image. `env_file:` only.
- Don't add a default `CMD` that runs one script — leaves the user a choice.
- Don't add a UI service yet (deferred; lives on the `app` branch).
- Don't introduce logging libraries or refactor `print()` calls — out of scope, and stdout works.
- Don't pin to `python:3.11-alpine` — matplotlib wheels are slow on musl; `slim` is the right tradeoff.
- Don't use the deprecated top-level `version:` key in `docker-compose.yaml`.
- Don't push large changes in one commit — one commit per step per CLAUDE.md.

---

## Verification (end-to-end)

1. **Clean-room build**: `docker compose build --no-cache` succeeds in <~3 min, image <500 MB.
2. **Report mode**: `docker compose run --rm app python generate_report.py` exits 0, writes `output/report.html` to host, browser shows charts.
3. **Q&A mode**: `docker compose run --rm app python main.py` reaches the prompt, answers a question, exits on `exit`.
4. **Logs**: `docker compose logs app` shows planner + per-item progress lines.
5. **CI**: `.github/workflows/ci.yml` goes green on push.
6. **No regressions**: `python main.py` and `python generate_report.py` still work outside Docker.
