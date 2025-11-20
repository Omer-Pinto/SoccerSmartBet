# LangSmith Integration Setup

This guide walks you through setting up LangSmith tracing and monitoring for the SoccerSmartBet system.

## What is LangSmith?

LangSmith is LangChain's observability and monitoring platform. It provides:
- **Tracing**: Detailed execution traces of your LangGraph flows
- **Debugging**: Step-by-step visibility into agent decisions and tool calls
- **Monitoring**: Performance metrics and error tracking
- **Analytics**: Aggregate statistics across runs

For SoccerSmartBet, LangSmith is essential for:
- Understanding which tools the Game/Team Intelligence Agents use
- Debugging failed data fetches or incorrect reports
- Monitoring LLM call counts and costs (~20-30 calls per run)
- Analyzing agent reasoning quality

---

## Prerequisites

1. **Python 3.13** installed
2. **LangChain packages** installed:
   ```bash
   pip install langchain langgraph langsmith
   ```
3. **LangSmith account** (free tier available)

---

## Step 1: Get Your LangSmith API Key

1. Go to [https://smith.langchain.com/](https://smith.langchain.com/)
2. Sign up or log in
3. Click your profile icon → **Settings**
4. Navigate to **API Keys** tab
5. Click **Create API Key**
6. Copy the generated key (you won't be able to see it again!)

---

## Step 2: Configure Environment Variables

1. Navigate to the project root:
   ```bash
   cd /path/to/SoccerSmartBet
   ```

2. Copy the example environment file:
   ```bash
   cp config/langsmith/.env.example config/langsmith/.env
   ```

3. Edit `config/langsmith/.env` and replace `your_key_here` with your actual API key:
   ```bash
   # config/langsmith/.env
   LANGSMITH_TRACING=true
   LANGSMITH_ENDPOINT=https://api.smith.langchain.com
   LANGSMITH_API_KEY=ls_proj_abc123...  # ← Your actual key here
   LANGSMITH_PROJECT=SoccerSmartBet
   ```

4. **Important**: Make sure `config/langsmith/.env` is in `.gitignore` to avoid committing secrets!

---

## Step 3: Verify Installation

Run the verification script to test your LangSmith connection:

```bash
python scripts/verify_langsmith.py
```

### Expected Output

```
============================================================
LangSmith Integration Verification
============================================================

Step 1: Loading environment variables...

Step 2: Verifying environment configuration...
✅ All required environment variables are set

Step 3: Testing LangSmith API connection...
🔄 Testing LangSmith API connection...
✅ Successfully connected to LangSmith API

Step 4: Testing LangGraph tracing...
🔄 Creating test LangGraph run...
✅ LangGraph test run completed successfully
   Final state: {'messages': ['Started test run', 'Processed successfully'], 'count': 2}

📊 Check your LangSmith dashboard:
   https://smith.langchain.com/o/YOUR_ORG/projects/p/SoccerSmartBet
   You should see a trace for 'LangGraph' with 2 nodes

============================================================
✅ ALL CHECKS PASSED
============================================================
```

---

## Step 4: Check Your Dashboard

1. Go to your LangSmith dashboard: [https://smith.langchain.com/](https://smith.langchain.com/)
2. Select the **SoccerSmartBet** project (it will be auto-created if it doesn't exist)
3. You should see a trace from the verification script
4. Click on the trace to explore:
   - Execution timeline
   - Node inputs/outputs
   - Duration metrics

---

## Using LangSmith in Your Flows

Once configured, LangSmith tracing is **automatic** for all LangGraph flows. No code changes needed!

The environment variables will be loaded by:
1. **Local development**: Your shell environment or `.env` files
2. **Production**: Docker container environment variables or secrets manager

### Example: Pre-Gambling Flow Tracing

When you run the Pre-Gambling Flow, LangSmith will automatically capture:

```
Pre-Gambling Flow Run
├── Smart Game Picker Node
│   ├── LLM Call: Analyze today's fixtures
│   └── Output: 5 selected games
├── Fetch Lines from winner.co.il
│   └── Output: 3 games with valid odds
├── [Parallel Subgraphs]
│   ├── Game Intelligence Agent (Game 1)
│   │   ├── fetch_h2h tool
│   │   ├── fetch_weather tool
│   │   ├── LLM Call: Analyze H2H patterns
│   │   └── Output: GameReport
│   ├── Team Intelligence Agent (Team 1)
│   │   ├── fetch_injuries tool
│   │   ├── fetch_form tool
│   │   ├── LLM Call: Assess injury impact
│   │   └── Output: TeamReport
│   └── ... (more parallel subgraphs)
└── Combine & Persist Reports
```

---

## Configuration Options

### Disable Tracing (Development)

To temporarily disable tracing during local testing:

```bash
# In config/langsmith/.env
LANGSMITH_TRACING=false
```

### Change Project Name

To use a different LangSmith project (e.g., for staging):

```bash
# In config/langsmith/.env
LANGSMITH_PROJECT=SoccerSmartBet-Staging
```

### Custom Endpoint (Self-Hosted)

If you're running a self-hosted LangSmith instance:

```bash
# In config/langsmith/.env
LANGSMITH_ENDPOINT=https://your-langsmith-instance.com
```

---

## Troubleshooting

### Error: "Missing or invalid environment variables"

**Problem**: The `.env` file doesn't exist or has placeholder values.

**Solution**:
1. Make sure you copied `.env.example` to `.env`
2. Replace `your_key_here` with your actual API key
3. Run `python scripts/verify_langsmith.py` again

---

### Error: "Failed to connect to LangSmith API"

**Problem**: Invalid API key or network issue.

**Solution**:
1. Verify your API key is correct (copy-paste from LangSmith dashboard)
2. Check your internet connection
3. Try regenerating your API key in LangSmith settings

---

### Error: "Missing required packages"

**Problem**: `langchain`, `langgraph`, or `langsmith` not installed.

**Solution**:
```bash
pip install langchain langgraph langsmith
```

Or if using a virtual environment:
```bash
source venv/bin/activate
pip install langchain langgraph langsmith
```

---

### Traces Not Appearing in Dashboard

**Problem**: Verification script passes, but no traces in LangSmith.

**Solution**:
1. Wait 30-60 seconds (traces can be delayed)
2. Refresh your LangSmith dashboard
3. Check you're viewing the correct project (`SoccerSmartBet`)
4. Verify `LANGSMITH_TRACING=true` in your `.env` file

---

### Permission Denied on `verify_langsmith.py`

**Problem**: Script not executable.

**Solution**:
```bash
chmod +x scripts/verify_langsmith.py
python scripts/verify_langsmith.py
```

---

## Production Deployment

### Docker Environment Variables

When deploying with Docker, pass LangSmith variables as environment variables:

```yaml
# docker-compose.yml
services:
  pre_gambling_flow:
    environment:
      - LANGSMITH_TRACING=true
      - LANGSMITH_ENDPOINT=https://api.smith.langchain.com
      - LANGSMITH_API_KEY=${LANGSMITH_API_KEY}  # From host .env
      - LANGSMITH_PROJECT=SoccerSmartBet-Production
```

### Kubernetes Secrets

For Kubernetes deployments, use secrets:

```bash
kubectl create secret generic langsmith-secret \
  --from-literal=api-key=ls_proj_abc123...
```

Then reference in your deployment:

```yaml
env:
  - name: LANGSMITH_API_KEY
    valueFrom:
      secretKeyRef:
        name: langsmith-secret
        key: api-key
```

---

## Best Practices

1. **Use separate projects for environments**: `SoccerSmartBet-Dev`, `SoccerSmartBet-Staging`, `SoccerSmartBet-Production`
2. **Never commit `.env` files**: Always use `.env.example` as template
3. **Rotate API keys regularly**: Especially for production environments
4. **Monitor LLM costs**: LangSmith shows token usage per run
5. **Set up alerts**: LangSmith can notify you of errors or anomalies

---

## Next Steps

- ✅ **Task 1.1**: Set up PostgreSQL schema to store reports LangSmith helps debug
- ✅ **Task 2.5**: Implement tools that LangSmith will trace
- ✅ **Task 4.2 & 5.2**: Build Intelligence Agents - LangSmith will show their reasoning
- 📊 **Monitor production**: Use LangSmith dashboards to track daily Pre-Gambling Flow runs

---

## Additional Resources

- [LangSmith Documentation](https://docs.smith.langchain.com/)
- [LangGraph Tracing Guide](https://langchain-ai.github.io/langgraph/how-tos/tracing/)
- [LangSmith Python SDK](https://github.com/langchain-ai/langsmith-sdk)
- [SoccerSmartBet Architecture](../../agents.md)

---

**Questions or issues?** Open an issue in the SoccerSmartBet repository with the `infrastructure` label.
