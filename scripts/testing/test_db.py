#!/usr/bin/env python3
"""Simple database connection test."""

import asyncio
import asyncpg
import os
import sys
from pathlib import Path

# Colors for terminal output
class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


async def test_direct_connection():
    """Test direct database connection using asyncpg."""
    print(f"\n{Colors.BOLD}{Colors.HEADER}JobSeeker AI - Database Connection Test{Colors.ENDC}")
    print("=" * 60)
    
    # Load environment variables from .env file
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                if line.strip() and not line.startswith("#"):
                    key, _, value = line.partition("=")
                    os.environ[key.strip()] = value.strip()
    
    # Get database credentials
    db_user = os.getenv("DB_USER", "jobseeker")
    db_password = os.getenv("DB_PASSWORD", "jobseeker123")
    db_name = os.getenv("DB_NAME", "jobseeker_db")
    db_host = os.getenv("DB_HOST", "localhost")
    db_port = os.getenv("DB_PORT", "5432")
    
    print(f"\n{Colors.CYAN}Database Configuration:{Colors.ENDC}")
    print(f"  Host: {db_host}:{db_port}")
    print(f"  Database: {db_name}")
    print(f"  User: {db_user}")
    
    try:
        # Try to connect
        print(f"\n{Colors.CYAN}Testing connection...{Colors.ENDC}")
        conn = await asyncpg.connect(
            host=db_host,
            port=int(db_port),
            user=db_user,
            password=db_password,
            database=db_name
        )
        
        print(f"{Colors.GREEN}✅ Successfully connected to PostgreSQL!{Colors.ENDC}")
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"\n{Colors.CYAN}PostgreSQL Version:{Colors.ENDC}")
        print(f"  {version}")
        
        # Check for pgvector extension
        extensions = await conn.fetch("""
            SELECT extname, extversion 
            FROM pg_extension 
            WHERE extname IN ('vector', 'uuid-ossp', 'pg_trgm')
        """)
        
        if extensions:
            print(f"\n{Colors.CYAN}Installed Extensions:{Colors.ENDC}")
            for ext in extensions:
                print(f"  - {ext['extname']} (v{ext['extversion']})")
        
        # Check for jobseeker schema and tables
        tables = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'jobseeker'
            ORDER BY table_name
        """)
        
        if tables:
            print(f"\n{Colors.CYAN}JobSeeker Schema Tables:{Colors.ENDC}")
            for table in tables:
                count = await conn.fetchval(f"SELECT COUNT(*) FROM jobseeker.{table['table_name']}")
                print(f"  - {table['table_name']}: {count} rows")
        else:
            print(f"\n{Colors.WARNING}⚠️  No tables found in jobseeker schema{Colors.ENDC}")
            print(f"  Run the init.sql script to create the schema")
        
        # Close connection
        await conn.close()
        
        print(f"\n{Colors.GREEN}✅ Database test completed successfully!{Colors.ENDC}\n")
        return True
        
    except asyncpg.PostgresError as e:
        print(f"\n{Colors.FAIL}❌ PostgreSQL Error: {e}{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Troubleshooting:{Colors.ENDC}")
        print("  1. Check if PostgreSQL container is running: docker ps")
        print("  2. Verify credentials in .env file")
        print("  3. Ensure database 'jobseeker_db' exists")
        return False
        
    except Exception as e:
        print(f"\n{Colors.FAIL}❌ Connection Error: {e}{Colors.ENDC}")
        print(f"\n{Colors.WARNING}Troubleshooting:{Colors.ENDC}")
        print("  1. Check if Docker is running: docker ps")
        print("  2. Start services: docker-compose up -d postgres")
        print("  3. Check logs: docker-compose logs postgres")
        return False


async def main():
    """Run all tests."""
    success = await test_direct_connection()
    
    if success:
        print(f"{Colors.GREEN}Next steps:{Colors.ENDC}")
        print("  1. Test API endpoints: python scripts/test_api.py")
        print("  2. Test job ingestion: python scripts/test_ingestion.py")
        print("  3. Run full test suite: python scripts/test_all.py")
    
    return 0 if success else 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)