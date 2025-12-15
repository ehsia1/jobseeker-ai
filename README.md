# JobSeeker AI 🎯

An intelligent job-seeking assistant that automatically finds, scores, and recommends personalized job opportunities for developers.

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Docker & Docker Compose
- Poetry (for dependency management)

### Setup Development Environment

```bash
# Clone the repository
git clone <repository-url>
cd jobseeker-ai

# Install dependencies
make dev-install

# Copy environment file and configure
cp .env.example .env
# Edit .env with your API keys and configuration

# Start services and initialize database
make setup
```

This will:
- Install all dependencies
- Start PostgreSQL, Redis, and ChromaDB containers
- Run database migrations
- Seed with sample data

### Development Commands

```bash
# Start development server
make dev-server

# Start background workers (in separate terminal)
make dev-worker

# Run tests
make test

# Format code
make format

# Run linting
make lint

# View logs
make docker-logs
```

## 🏗️ Project Structure

```
jobseeker-ai/
├── backend/                 # Python FastAPI backend
│   ├── agents/             # LangGraph AI agent orchestration
│   ├── api/                # REST API routes & schemas
│   ├── models/             # SQLAlchemy ORM models
│   ├── parsers/            # JD & resume parsing
│   ├── scorers/            # Job matching algorithms
│   ├── searchers/          # Multi-source job aggregation
│   ├── services/           # Business logic services
│   └── workers/            # Celery background tasks
├── frontend/
│   └── web/               # Next.js 15 + React 19 dashboard
├── infrastructure/        # Docker, Terraform, K8s configs
├── scripts/               # Utility & testing scripts
└── tests/                 # Pytest test suites
```

## 🛠️ Technology Stack

- **Backend**: Python (FastAPI, SQLAlchemy, Celery)
- **Database**: PostgreSQL with pgvector extension
- **Cache**: Redis
- **Vector DB**: ChromaDB
- **AI/ML**: LangChain, OpenAI, Anthropic Claude
- **Infrastructure**: Docker, AWS Lambda, Terraform
- **Monitoring**: Prometheus, Grafana, Sentry

## 📊 Core Features

### 🔍 Multi-Source Job Aggregation
- Email alerts from Upwork, LinkedIn, Indeed
- RSS feeds from Remote OK, WeWorkRemotely
- Public APIs from AngelList, Stack Overflow

### 🤖 AI-Powered Matching
- Semantic similarity using embeddings
- Keyword-based skill matching
- ML-driven personalization
- Contextual job scoring

### ✍️ Intelligent Proposal Generation
- Personalized pitch creation
- Relevant experience highlighting
- Custom templates per platform

### 📈 Learning System
- Feedback-driven improvements
- Multi-armed bandit optimization
- User preference adaptation

## 📱 Mobile Development

### iOS Simulator Testing

To test file uploads (resumes, documents) on the iOS simulator, you need to transfer files to the simulator's file system.

**Loading test files onto iOS Simulator:**

1. Place your test files in the `samples/` folder (gitignored)
2. Start a local file server:
   ```bash
   cd samples
   python3 -m http.server 8888
   ```
3. In the iOS simulator:
   - Open Safari
   - Navigate to `http://localhost:8888`
   - Tap your file (e.g., `resume.pdf`)
   - Tap Share → "Save to Files"
4. The file is now available in the Files app for document picker access

### Running the Mobile App

```bash
cd frontend/mobile

# Install dependencies
npm install

# Start Expo development server
npx expo start

# Run on iOS simulator
npx expo run:ios

# Run on Android emulator
npx expo run:android
```

## 🧪 Development Workflow

### Running Tests

```bash
# All tests
make test

# Unit tests only
make test-unit

# Integration tests
make test-integration

# With coverage report
poetry run pytest --cov=backend --cov-report=html
```

### Code Quality

```bash
# Format code
make format

# Check linting
make lint

# Type checking
make type-check

# Pre-commit hooks
make pre-commit
```

### Database Operations

```bash
# Create migration
make migrate-create

# Apply migrations
make migrate

# Seed test data
make seed
```

## 🔧 Configuration

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/db

# AI Services
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here

# Email Ingestion
EMAIL_ADDRESS=your_email@gmail.com
EMAIL_PASSWORD=your_app_password

# Slack Integration
SLACK_BOT_TOKEN=xoxb-your-token
```

## 🚀 Deployment

### Docker Production

```bash
# Build production image
docker-compose -f docker-compose.prod.yml build

# Deploy
docker-compose -f docker-compose.prod.yml up -d
```

### AWS Lambda

```bash
# Deploy with Terraform
cd infrastructure/terraform
terraform init
terraform plan
terraform apply
```

## 📈 Monitoring & Observability

- **Health Checks**: `/health` endpoint
- **Metrics**: Prometheus metrics at `:9090/metrics`
- **Logs**: Structured JSON logging
- **Tracing**: Sentry integration
- **Celery**: Flower dashboard at `:5555`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run `make pre-commit`
6. Submit a pull request

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/your-repo/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/discussions)
- **Email**: support@jobseeker-ai.com