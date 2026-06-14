# C2P Platform API

FastAPI backend for Contract-to-Payment Compliance Platform.

## Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 14+

### Installation

```bash
cd apps/api

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -e .

# Copy environment file
cp .env.example .env
# Edit .env with your database URL and secret key
```

### Database Setup

```bash
# Create database
createdb c2p_platform

# Run migrations
alembic upgrade head
```

### Run Development Server

```bash
uvicorn app.main:app --reload --port 8000
```

API available at `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### Run Tests

```bash
pytest -v
```

## Project Structure

```
apps/api/
├── app/
│   ├── api/
│   │   ├── deps.py           # Dependencies (auth, db)
│   │   └── v1/
│   │       ├── auth.py       # Auth endpoints
│   │       └── users.py      # User endpoints
│   ├── core/
│   │   ├── config.py         # Settings
│   │   ├── database.py       # DB connection
│   │   └── security.py       # JWT, password hashing
│   ├── models/
│   │   └── user.py           # User SQLAlchemy model
│   ├── schemas/
│   │   └── user.py           # Pydantic schemas
│   ├── services/
│   │   └── user_service.py   # Business logic
│   ├── main.py               # FastAPI app
│   └── __init__.py
├── alembic/
│   ├── env.py                # Migration config
│   └── versions/
│       └── 001_initial_migration.py
├── tests/
│   ├── conftest.py           # Test fixtures
│   └── test_auth.py          # Auth tests
├── pyproject.toml
├── alembic.ini
├── .env.example
├── Dockerfile
└── README.md
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login, returns JWT token |

### Users (Protected)
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/v1/users/me` | Get current user profile |
| PATCH | `/api/v1/users/me` | Update current user profile |

### Health
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/` | Root endpoint |

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/c2p_platform` |
| `SECRET_KEY` | JWT signing key (min 32 chars) | Required |
| `ALGORITHM` | JWT algorithm | `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token expiry | `43200` (30 days) |
| `BCRYPT_ROUNDS` | Password hash rounds | `12` |
| `DEBUG` | Debug mode | `True` |

## Example Usage

### Register
```bash
curl -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "full_name": "John Doe", "password": "securepass123"}'
```

### Login
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "securepass123"}'
```

### Get Profile (with token)
```bash
curl -X GET http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <your_token>"
```

### Update Profile
```bash
curl -X PATCH http://localhost:8000/api/v1/users/me \
  -H "Authorization: Bearer <your_token>" \
  -H "Content-Type: application/json" \
  -d '{"full_name": "Jane Doe"}'
```