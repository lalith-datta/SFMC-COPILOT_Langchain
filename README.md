# SFMC-COPILOT
This is the SFMC COPILOT which will do the tasks such as creating DE's, Emails, Automation etc

## Project Structure

| Module | Path | Tech Stack |
|--------|------|------------|
| **Backend** | `sfmc-copilot-backend-python/` | Python 3.13, FastAPI, Google Gemini SDK, Ollama |
| **Frontend** | `sfmc-copilot-frontend/` | React 19, Vite 7 |
| ~~Legacy Backend~~ | `sfmc-copilot-backend/` | ~~Java Spring Boot~~ (migrated to Python) |

---

## Quick Start

### 1. Backend

```bash
cd sfmc-copilot-backend-python

# (Optional) Create a virtual environment
python3 -m venv venv && source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Copy env file and configure
cp .env.example .env
# Edit .env with your GEMINI_API_KEY, SFMC credentials, etc.

# Start the server (port 8080, hot-reload enabled)
python main.py
```

### 2. Frontend

```bash
cd sfmc-copilot-frontend
npm install
npm run dev
# Opens at http://localhost:5173
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | For Gemini | Google AI Studio API key |
| `SFMC_CLIENT_ID` | For SFMC | SFMC installed package client ID |
| `SFMC_CLIENT_SECRET` | For SFMC | SFMC installed package client secret |
| `SFMC_AUTH_BASE_URI` | For SFMC | SFMC auth endpoint |
| `SFMC_REST_BASE_URI` | For SFMC | SFMC REST API base URL |

> **Note:** The app works in **demo mode** without any env vars configured — SFMC operations return realistic mock responses, and LLM calls require either Gemini key or local Ollama running.
