# SFMC Copilot Backend (Python)

AI-powered Salesforce Marketing Cloud assistant built with **FastAPI**, **LangChain**, and **Google Gemini**.

The LLM automatically decides when to call SFMC tools (create Data Extensions, list DEs, create emails, etc.) using LangChain's Agent framework — no manual intent detection needed.

---

## Prerequisites

### 1. Install Python 3.11+

**macOS (Homebrew):**
```bash
brew install python@3.13
```

**Ubuntu/Debian:**
```bash
sudo apt update && sudo apt install python3 python3-pip python3-venv
```

**Windows:**
Download from [python.org](https://www.python.org/downloads/) and check "Add Python to PATH" during install.

**Verify installation:**
```bash
python3 --version
# Expected: Python 3.11.x or higher

pip3 --version
# Expected: pip 24.x or higher
```

### 2. Install Git (if not already installed)

```bash
git --version
# If not installed:
# macOS: brew install git
# Ubuntu: sudo apt install git
# Windows: https://git-scm.com/downloads
```

---

## Setup

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd SFMC_copilot_python/sfmc-copilot-backend-python
```

### 2. Create a virtual environment (recommended)

```bash
python3 -m venv venv
```

**Activate it:**
```bash
# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

**Verify you're in the venv:**
```bash
which python3
# Should show: .../sfmc-copilot-backend-python/venv/bin/python3
```

### 3. Install dependencies

```bash
pip3 install -r requirements.txt
```

**Verify key packages installed:**
```bash
pip3 list | grep -E "fastapi|langchain|uvicorn"
# Should show fastapi, langchain, langchain-google-genai, uvicorn, etc.
```

### 4. Configure environment variables

Create a `.env` file in this directory:

```bash
cp .env.example .env   # if .env.example exists, or create manually:
```

```env
# === REQUIRED ===

# Google Gemini API Key (get from https://aistudio.google.com/apikey)
GEMINI_API_KEY=your_gemini_api_key_here

# === SFMC Credentials (get from SFMC Setup > Apps > Installed Packages) ===
SFMC_CLIENT_ID=your_sfmc_client_id
SFMC_CLIENT_SECRET=your_sfmc_client_secret
SFMC_AUTH_BASE_URI=https://YOUR_SUBDOMAIN.auth.marketingcloudapis.com
SFMC_REST_BASE_URI=https://YOUR_SUBDOMAIN.rest.marketingcloudapis.com

# === OPTIONAL ===

# Server port (default: 8080)
# SERVER_PORT=8080

# Gemini model (default: gemini-2.5-flash)
# GEMINI_MODEL=gemini-2.5-flash
```

> **Important:** Both `GEMINI_API_KEY` and all four `SFMC_*` variables are required for the app to function. Without SFMC credentials, API calls will fail with a configuration error.

---

## Running the Backend

### Start the server

```bash
python3 main.py
```

You should see:
```
SFMC Copilot Backend (Python / FastAPI + LangChain)
Server running on http://localhost:8080
Gemini configured: True
SFMC configured: True
```

The server runs on **port 8080** with hot-reload enabled — any code changes auto-restart the server.

### Verify the server is running(OPTIONAL)

```bash
curl http://localhost:8080/api/health
```

Expected response:
```json
{"status": "UP", "service": "SFMC Copilot Backend"}
```

### Test a chat request

```bash
curl -X POST http://localhost:8080/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is a Data Extension?", "conversationId": "test1", "preferredModel": "gemini"}'
```

---

## Stopping the Server

Press `Ctrl+C` in the terminal.

If the port is stuck (e.g., `Address already in use` error):
```bash
# Find and kill the process using port 8080
lsof -ti:8080 | xargs kill -9
```

---

## Project Structure

```
sfmc-copilot-backend-python/
├── main.py                  # FastAPI entry point, CORS, server startup
├── config.py                # Environment variable loading (pydantic-settings)
├── requirements.txt         # Python dependencies
├── .env                     # Your environment variables (not in git)
├── models/
│   ├── __init__.py
│   └── schemas.py           # Pydantic request/response models
├── routers/
│   ├── __init__.py
│   └── chat.py              # POST /api/chat, GET /api/health endpoints
└── services/
    ├── __init__.py
    ├── ai_gateway.py         # LangChain Agent with Gemini + tool calling + memory
    ├── sfmc_tools.py          # @tool definitions (create DE, list DEs, etc.)
    ├── sfmc_api.py            # SFMC REST API client (httpx)
    └── sfmc_auth.py           # SFMC OAuth2 token management
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/chat` | Send a message to the AI copilot |
| `GET`  | `/api/health` | Check backend health status |

### POST /api/chat

**Request body:**
```json
{
  "message": "Create a data extension called Users with Name and Email fields",
  "conversationId": "abc123",
  "preferredModel": "gemini"
}
```

**Response:**
```json
{
  "text": "✅ Data Extension 'Users' created successfully in SFMC!...",
  "model": "gemini"
}
```

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `Address already in use` | Run `lsof -ti:8080 \| xargs kill -9` then restart |
| `GEMINI_API_KEY not configured` | Add your Gemini API key to the `.env` file |
| `SFMC credentials not configured` | Add all four `SFMC_*` variables to `.env` |
| `429 RESOURCE_EXHAUSTED` | Gemini free-tier limit hit (20 req/day). Wait or upgrade plan |
| `ModuleNotFoundError` | Run `pip3 install -r requirements.txt` again |
| Server not reloading on changes | Ensure you're running `python3 main.py`, not `uvicorn` directly |
