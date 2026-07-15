# AI Intelligence OS — Backend

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## Development Server

```bash
uvicorn main:app --reload --port 8000
```

## Run Tests

```bash
pytest
```

## Lint

```bash
ruff check .
ruff format .
mypy .
```
