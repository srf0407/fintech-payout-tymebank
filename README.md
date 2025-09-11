# Fintech Payouts (TymeBank) - Full-Stack Application

A secure, observable, and reliable fintech application for payout processing with OAuth 2.0 authentication, real-time status updates, and comprehensive security features.

## 🏗️ Architecture Overview

### Backend (FastAPI + PostgreSQL)
- **FastAPI** with async/await patterns
- **PostgreSQL** database with async SQLAlchemy 2.0
- **OAuth 2.0** authentication with Google (state, nonce, PKCE)
- **JWT** tokens for session management
- **Mock Payment Provider** with realistic error simulation
- **Webhook** processing with HMAC/JWT signature verification
- **Rate limiting** and **idempotency** enforcement
- **Structured logging** with correlation IDs

### Frontend (React + TypeScript)
- **React 19** with TypeScript
- **Material-UI** components
- **Real-time polling** for payout status updates
- **OAuth** integration with secure token handling
- **Error boundaries** and comprehensive error handling
- **Responsive design** with modern UX

## 🚀 Quick Start

### Prerequisites
- **Python 3.9+**
- **Node.js 18+**
- **Docker** (for PostgreSQL)
- **Git**

### 1. Clone Repository
```bash
git clone <repository-url>
cd fintech-payout-tymebank
```

### 2. Backend Setup

#### Environment Configuration
Create `backend/app/.env` file:
```env
# Database
POSTGRES_USER=your_db_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_DB=your_database_name
DATABASE_URL=postgresql+asyncpg://your_db_user:your_secure_password@localhost:5433/your_database_name

# Security (Generate secure random strings)
SECRET_KEY=your-super-secret-key-minimum-32-characters-long
WEBHOOK_SECRET=your-webhook-secret-minimum-32-characters-long

# OAuth 2.0 (Google) - Get these from Google Cloud Console
GOOGLE_CLIENT_ID=your-google-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/callback

# Application Settings
DEBUG=false
LOG_LEVEL=INFO
ACCESS_TOKEN_EXPIRE_MINUTES=30
WEBHOOK_TIMEOUT_SECONDS=300
RATE_LIMIT_PER_MINUTE=10

# Payment Provider
PAYMENT_PROVIDER_BASE_URL=http://localhost:8000/mock-provider
PAYMENT_PROVIDER_TIMEOUT=30

# CORS
CORS_ALLOW_ORIGINS=["http://localhost:3000", "http://localhost:5173"]
FRONTEND_URL=http://localhost:5173
```

#### Database Setup
```bash
# Start PostgreSQL with Docker
docker compose up -d db

# Run database migrations
./venv/Scripts/alembic.exe -c backend/app/db/alembic.ini upgrade head

# Verify database setup
docker exec -it fintech_postgres psql -U your_db_user -d your_database_name -c "\dt"
```

#### Install Dependencies & Run Backend
```bash
# Create virtual environment (if not exists)
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Install dependencies
pip install fastapi uvicorn sqlalchemy[asyncio] asyncpg alembic pydantic python-jose[cryptography] python-dotenv httpx

# Run the API server
./venv/Scripts/uvicorn.exe backend.app.main:app --reload --host 0.0.0.0 --port 8000
```

### 3. Frontend Setup

#### Install Dependencies & Run Frontend
```bash
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

### 4. Access the Application
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🧪 Testing

### Backend Tests
```bash
# Run all tests
cd backend
python -m pytest app/tests/ -v

# Run specific test categories
python -m pytest app/tests/test_security.py -v
python -m pytest app/tests/test_payouts_api.py -v
python -m pytest app/tests/integration/ -v



## 📚 API Documentation

### Authentication Endpoints
- `POST /auth/login` - Initiate OAuth 2.0 login
- `GET /auth/callback` - Handle OAuth callback
- `POST /auth/refresh` - Refresh access token
- `POST /auth/logout` - Logout user
- `GET /auth/me` - Get current user info

### Payout Endpoints
- `POST /payouts` - Create payout (requires `Idempotency-Key` header)
- `GET /payouts?page=N&page_size=M` - List paginated payouts

### Webhook Endpoints
- `POST /webhooks/payments` - Receive payment webhooks

### Health Check
- `GET /health` - Health check endpoint

## 🔐 Security Features

### OAuth 2.0 Security
- **State parameter** with cryptographic signature
- **PKCE** (Proof Key for Code Exchange) implementation
- **Nonce** for replay attack prevention
- **Secure token storage** in HTTP-only cookies

### Webhook Security
- **HMAC SHA256** signature verification
- **JWT** signature verification
- **Timestamp validation** (replay attack protection)
- **Idempotency** handling

### Rate Limiting
- **Per-user** payout creation limits
- **Authentication endpoint** rate limiting
- **Configurable** rate limits per endpoint

### Data Protection
- **Input validation** with Pydantic models
- **SQL injection** protection via SQLAlchemy ORM
- **XSS protection** via proper encoding
- **CSRF protection** via SameSite cookies

## 🔄 Key Features

### Real-time Updates
- **Polling service** for payout status updates
- **WebSocket-like** experience with HTTP polling
- **Automatic retry** logic with exponential backoff

### Mock Payment Provider
- **Realistic error simulation** (rate limits, timeouts, etc.)
- **Configurable error rates** for testing
- **Webhook callbacks** with delays
- **Status progression** simulation

### Observability
- **Structured logging** with correlation IDs
- **Request/response** logging
- **Performance metrics** in logs
- **Error tracking** with context

### Error Handling
- **Graceful degradation** for API failures
- **User-friendly** error messages
- **Retry mechanisms** for transient errors
- **Circuit breaker** patterns

## 🚀 Deployment

### Production Considerations
1. **Environment Variables**: Use secure secret management
2. **Database**: Use managed PostgreSQL service
3. **HTTPS**: Enable SSL/TLS certificates
4. **Monitoring**: Set up application monitoring
5. **Logging**: Configure centralized logging
6. **Scaling**: Consider horizontal scaling for high load

### Docker Deployment
```bash
# Build and run with Docker Compose
docker compose up --build

# Production deployment
docker compose -f docker-compose.prod.yml up -d
```




**Built with ❤️ for secure fintech applications**