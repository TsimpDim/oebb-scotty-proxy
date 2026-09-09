# transport

Simple FastAPI service for transport data.

## Prerequisites

- Python 3.13+
- `uv` installed: https://docs.astral.sh/uv/

## Setup

1. Clone the repository.
2. Move into the project folder.
3. Install dependencies:

```bash
uv sync
```

## Run the app

Start the development server:

```bash
uv run dev
```

The API will be available at:

- http://127.0.0.1:8000
- Docs UI: http://127.0.0.1:8000/docs

## Available endpoint

- `GET /stations`
- `GET /stations/{station_id}`
