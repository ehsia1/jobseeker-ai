#!/usr/bin/env python3
"""Development startup script."""

import asyncio
import sys
import os
from pathlib import Path

# Add backend to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

async def main():
    """Start development services."""
    
    print("🚀 Starting JobSeeker AI development environment...")
    
    # Import after path setup
    from backend.config import settings
    from backend.database import init_db
    
    print(f"Environment: {settings.environment}")
    print(f"Database URL: {settings.database_url}")
    
    try:
        print("📊 Initializing database...")
        await init_db()
        print("✅ Database initialized successfully")
        
        print("🔥 Starting FastAPI server...")
        print("API will be available at: http://localhost:8080")
        print("API docs: http://localhost:8080/docs")
        
        # Start uvicorn server
        import uvicorn
        uvicorn.run(
            "backend.api.main:app",
            host="0.0.0.0",
            port=8080,
            reload=True,
            reload_dirs=["backend"]
        )
        
    except Exception as e:
        print(f"❌ Error starting application: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)