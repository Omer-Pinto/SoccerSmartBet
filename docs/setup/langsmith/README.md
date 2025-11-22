# LangSmith Integration Setup

LangSmith provides observability for LangGraph flows: tracing, debugging, and performance monitoring.

## Prerequisites

- Python 3.13
- LangSmith account (free tier): [https://smith.langchain.com/](https://smith.langchain.com/)
- Install packages: `pip install langchain langgraph langsmith python-dotenv`

## Setup Steps

### 1. Get API Key

1. Go to [smith.langchain.com](https://smith.langchain.com/) and sign in
2. Settings → API Keys → Create API Key
3. Copy the key (it won't be shown again)

### 2. Configure Environment

```bash
# Copy example file to project root
cp .env.example .env

# Edit .env and add your LangSmith API key:
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=ls_proj_abc123...  # Your actual key
LANGSMITH_PROJECT=SoccerSmartBet
```

**Important**: `.env` is already in `.gitignore` - never commit it!

### 3. Verify Setup

Run the integration tests:

```bash
pytest tests/system/test_langsmith_integration.py -v
```

All tests should pass. Tests automatically verify that traces are created in LangSmith.

## Usage

Once configured, tracing is **automatic** - no code changes needed.

**Toggle tracing:** Set `LANGSMITH_TRACING=false` to disable  
**Different projects:** Change `LANGSMITH_PROJECT=SoccerSmartBet-Staging`

## Production

Pass variables via Docker environment or Kubernetes secrets. Example:

```yaml
services:
  app:
    environment:
      - LANGSMITH_TRACING=true
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}
      - LANGSMITH_PROJECT=SoccerSmartBet-Production
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Tests fail ".env not found" | Copy `.env.example` to `.env` at project root |
| Tests fail "placeholder value" | Replace `your_key_here` with actual key in `.env` |
| API connection fails | Verify key, check internet |
| No traces in dashboard | Wait 60s, refresh, verify `LANGSMITH_TRACING=true` in `.env` |

**Resources:** [LangSmith Docs](https://docs.smith.langchain.com/) · [LangGraph Tracing](https://langchain-ai.github.io/langgraph/how-tos/tracing/)
