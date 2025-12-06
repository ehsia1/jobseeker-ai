# 🚀 JobSeeker AI - Quick Start Guide

## Prerequisites

- Python 3.11+
- Docker & Docker Compose
- Poetry (or pip)

## 🔧 Initial Setup (5 minutes)

### 1. Clone and Install Dependencies

```bash
# Clone the repository
git clone <your-repo-url>
cd jobseeker-ai

# Install Python dependencies
poetry install
# OR with pip:
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your credentials:

```bash
# Required for database
DB_USER=jobseeker
DB_PASSWORD=jobseeker123
DATABASE_URL=postgresql+asyncpg://jobseeker:jobseeker123@localhost:5432/jobseeker_db

# Required for authentication
SECRET_KEY=your-secret-key-change-this-in-production

# Optional (for email ingestion)
EMAIL_ADDRESS=your-email@gmail.com
EMAIL_PASSWORD=your-app-specific-password

# Optional (for AI features)
OPENAI_API_KEY=your-openai-key
```

### 3. Start Services

```bash
# Start database and Redis
docker-compose up -d

# Wait for services to be ready (about 10 seconds)
sleep 10

# Run database migrations
poetry run alembic upgrade head
# OR
make migrate

# Start the API server
make dev-server
# OR
poetry run uvicorn backend.api.main:app --reload --host 0.0.0.0 --port 8080
```

## 🧪 Test Everything

### Run Comprehensive Test

```bash
make test-all
```

This will test:
- ✅ Database connection
- ✅ API server
- ✅ Authentication system
- ✅ Job ingestion pipeline
- ✅ AI matching system
- ✅ Sample data creation

Expected output:
```
=== Test Summary ===
  Database: ✅ PASS
  API: ✅ PASS
  Auth: ✅ PASS
  Ingestion: ✅ PASS
  Matching: ✅ PASS
  Sample: ✅ PASS

Result: 6/6 tests passed
🎉 All systems operational!
```

## 📊 Using the System

### 1. Access API Documentation

Open in browser: http://localhost:8080/docs

### 2. Create a User Account

```bash
# Register
curl -X POST http://localhost:8080/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "myuser",
    "password": "MyPassword123"
  }'

# Login
curl -X POST http://localhost:8080/auth/login \
  -F "username=myuser" \
  -F "password=MyPassword123"

# Save the token from response
```

### 3. Update Your Profile

```bash
# Set your skills and preferences
curl -X PUT http://localhost:8080/users/profile \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "skills": ["python", "aws", "docker"],
    "experience_years": 5,
    "min_rate_usd": 80,
    "preferences": {
      "remote_only": true,
      "industries": ["Tech", "SaaS"]
    }
  }'
```

### 4. Trigger Job Ingestion

```bash
# Test ingestion (without storing)
make test-ingestion

# Trigger real ingestion (if email configured)
curl -X POST http://localhost:8080/ingestion/trigger \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### 5. Generate Job Matches

```bash
# Generate matches for your profile
curl -X POST http://localhost:8080/matching/generate \
  -H "Authorization: Bearer YOUR_TOKEN"

# View your matches
curl http://localhost:8080/matches?min_score=70 \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 🛠️ Development Commands

```bash
# Start all services
make setup

# Run tests
make test           # All tests
make test-ingestion # Test job ingestion
make test-matching  # Test AI matching

# Database operations
make migrate        # Run migrations
make seed          # Add test data

# Background workers (for scheduled tasks)
make dev-worker    # Start Celery worker
make dev-beat      # Start Celery beat scheduler

# Monitoring
make celery-monitor # Flower dashboard at :5555

# Cleanup
make docker-down   # Stop services
make clean         # Remove build artifacts
```

## 📁 Project Structure

```
jobseeker-ai/
├── backend/
│   ├── api/         # REST API endpoints
│   ├── models/      # Database models
│   ├── parsers/     # Job parsers (email, RSS)
│   ├── scorers/     # AI matching algorithms
│   ├── services/    # Business logic
│   └── workers/     # Background tasks
├── scripts/         # Test and utility scripts
├── infrastructure/  # Docker, Terraform configs
└── docs/           # Documentation
```

## 🔍 Troubleshooting

### Database Connection Error
```bash
# Check if PostgreSQL is running
docker-compose ps

# Restart database
docker-compose restart postgres
```

### API Server Won't Start
```bash
# Check port availability
lsof -i :8080

# Check logs
docker-compose logs -f
```

### No Jobs Found
```bash
# Create sample jobs
make test-all  # This creates sample data

# Or manually ingest from RSS
make test-ingestion
```

### Matching Not Working
```bash
# Test embedding service
make test-matching

# Check if jobs exist
curl http://localhost:8080/jobs \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## 📈 What's Working

✅ **Complete Features:**
- User authentication (JWT)
- Profile management
- Job ingestion from RSS/email
- AI-powered job matching
- Similarity scoring
- RESTful API
- Background task processing

🚧 **In Progress:**
- LangChain agent integration
- Proposal generation
- Email notifications
- Slack bot
- Web dashboard

## 🆘 Getting Help

1. Check API docs: http://localhost:8080/docs
2. Run tests: `make test-all`
3. Review logs: `docker-compose logs -f`
4. Check configuration: Ensure `.env` is properly configured

## 🎉 Success Checklist

- [ ] Docker services running
- [ ] Database migrations applied
- [ ] API server accessible
- [ ] User account created
- [ ] Profile configured
- [ ] Sample jobs loaded
- [ ] Matches generated
- [ ] All tests passing

If all checks pass, your JobSeeker AI is ready to use!