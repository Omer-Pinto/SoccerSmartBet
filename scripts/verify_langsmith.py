#!/usr/bin/env python3
"""
LangSmith Integration Verification Script

This script tests the LangSmith connection and tracing functionality
by creating a simple LangGraph test run and verifying the trace appears
in the LangSmith dashboard.

Usage:
    python scripts/verify_langsmith.py

Requirements:
    - LangSmith API key configured in config/langsmith/.env
    - langchain, langgraph, and langsmith packages installed
"""

import os
import sys
from pathlib import Path
from typing import TypedDict, Annotated

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def load_env():
    """Load environment variables from config/langsmith/.env"""
    env_path = project_root / "config" / "langsmith" / ".env"
    
    if not env_path.exists():
        print("❌ Error: config/langsmith/.env not found")
        print("Please copy config/langsmith/.env.example to config/langsmith/.env")
        print("and fill in your LangSmith API key")
        return False
    
    # Simple .env parser (for production, use python-dotenv)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                key, value = line.split('=', 1)
                os.environ[key.strip()] = value.strip()
    
    return True


def verify_env_vars():
    """Verify all required environment variables are set"""
    required_vars = [
        'LANGSMITH_TRACING',
        'LANGSMITH_ENDPOINT',
        'LANGSMITH_API_KEY',
        'LANGSMITH_PROJECT'
    ]
    
    missing = []
    for var in required_vars:
        value = os.environ.get(var)
        if not value or value == 'your_key_here':
            missing.append(var)
    
    if missing:
        print("❌ Error: Missing or invalid environment variables:")
        for var in missing:
            print(f"   - {var}")
        return False
    
    print("✅ All required environment variables are set")
    return True


def test_langsmith_connection():
    """Test LangSmith connection by creating a simple trace"""
    try:
        from langsmith import Client
        
        client = Client(
            api_key=os.environ['LANGSMITH_API_KEY'],
            api_url=os.environ['LANGSMITH_ENDPOINT']
        )
        
        # Test connection by checking if we can access the API
        print("🔄 Testing LangSmith API connection...")
        
        # This will raise an exception if credentials are invalid
        projects = list(client.list_projects(limit=1))
        
        print("✅ Successfully connected to LangSmith API")
        return True
        
    except Exception as e:
        print(f"❌ Failed to connect to LangSmith API: {e}")
        return False


def test_langgraph_tracing():
    """Create a simple LangGraph run and verify tracing works"""
    try:
        from langgraph.graph import StateGraph, END
        from operator import add
        
        print("🔄 Creating test LangGraph run...")
        
        # Define a simple state
        class TestState(TypedDict):
            messages: Annotated[list[str], add]
            count: int
        
        # Create a simple graph
        def start_node(state: TestState) -> TestState:
            return {
                "messages": ["Started test run"],
                "count": state.get("count", 0) + 1
            }
        
        def process_node(state: TestState) -> TestState:
            return {
                "messages": ["Processed successfully"],
                "count": state["count"] + 1
            }
        
        # Build graph
        graph = StateGraph(TestState)
        graph.add_node("start", start_node)
        graph.add_node("process", process_node)
        graph.set_entry_point("start")
        graph.add_edge("start", "process")
        graph.add_edge("process", END)
        
        # Compile and run
        app = graph.compile()
        
        result = app.invoke({"messages": [], "count": 0})
        
        print("✅ LangGraph test run completed successfully")
        print(f"   Final state: {result}")
        
        # Give LangSmith a moment to process the trace
        import time
        time.sleep(2)
        
        print("\n📊 Check your LangSmith dashboard:")
        project_name = os.environ['LANGSMITH_PROJECT']
        print(f"   https://smith.langchain.com/o/YOUR_ORG/projects/p/{project_name}")
        print("   You should see a trace for 'LangGraph' with 2 nodes")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing required packages: {e}")
        print("   Install with: pip install langchain langgraph langsmith")
        return False
    except Exception as e:
        print(f"❌ Failed to create LangGraph test run: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main verification workflow"""
    print("=" * 60)
    print("LangSmith Integration Verification")
    print("=" * 60)
    print()
    
    # Step 1: Load environment variables
    print("Step 1: Loading environment variables...")
    if not load_env():
        return 1
    print()
    
    # Step 2: Verify all required vars are set
    print("Step 2: Verifying environment configuration...")
    if not verify_env_vars():
        return 1
    print()
    
    # Step 3: Test LangSmith API connection
    print("Step 3: Testing LangSmith API connection...")
    if not test_langsmith_connection():
        return 1
    print()
    
    # Step 4: Test LangGraph tracing
    print("Step 4: Testing LangGraph tracing...")
    if not test_langgraph_tracing():
        return 1
    print()
    
    print("=" * 60)
    print("✅ ALL CHECKS PASSED")
    print("=" * 60)
    print()
    print("Next steps:")
    print("1. Check your LangSmith dashboard for the test trace")
    print("2. If you see the trace, LangSmith integration is working!")
    print("3. You can now use LangSmith tracing in your SoccerSmartBet flows")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
