# Production Deployment Guide

This guide describes the configuration requirements, Docker orchestration, and best practices for deploying the C2P Platform to production.

---

## 🌎 Deployment Architecture

In a production environment, the frontend and backend are decoupled:
* **Frontend:** Compiled to static HTML/JS/CSS assets and served via a Content Delivery Network (CDN) or web server (e.g., Nginx, Cloudflare Pages, AWS S3).
* **Backend:** Scaled across containerized instances (e.g., AWS ECS, Kubernetes, GCP Cloud Run) fronted by a Load Balancer and connected to a managed PostgreSQL cluster.

---

## 🔒 Production Environment Variables

Never commit a `.env` file to production. Environment variables must be injected securely via your cloud provider (e.g., AWS Parameter Store, GCP Secret Manager, Vault).

### Backend Variables (`c2p-platform/apps/api`)

| Name | Expected Value / Type | Purpose |
|---|---|---|
| `DEBUG` | `False` (Boolean) | Disables Swagger debug profiles and tracebacks. |
| `DATABASE_URL` | `postgresql+asyncpg://<user>:<password>@<host>:5432/<db_name>` | Managed PostgreSQL connection string (must use `asyncpg`). |
| `SECRET_KEY` | High-entropy random string (at least 64 hex characters) | Used for signing JWT access tokens securely. |
| `ALGORITHM` | `HS256` (String) | Signature algorithm for JWT tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `60` (Integer, equivalent to 1 hour) | Recommended production value (limit token lifetimes). |
| `BCRYPT_ROUNDS` | `12` (Integer) | Computational difficulty for password hashing. |
| `UPLOAD_DIR` | Absolute path (e.g. `/var/c2p/uploads`) | Storage directory for uploaded documents. |
| `MAX_FILE_SIZE_MB` | `20` (Integer) | Maximum file upload size. |

---

## 📦 Containerization (Docker)

### 1. Backend Dockerfile
The API includes a production-ready **[Dockerfile](file:///c:/Users/Prashanth/Downloads/C2P-Platform/C2P-Platform/c2p-platform/apps/api/Dockerfile)**.

To build the backend container locally:
```bash
cd c2p-platform/apps/api
docker build -t c2p-api:latest .
```

To run the container:
```bash
docker run -d -p 8000:8000 \
  -e DATABASE_URL="postgresql+asyncpg://postgres:securepass@host:5432/db" \
  -e SECRET_KEY="your-prod-secret-key-must-be-very-long-and-random-here" \
  -e DEBUG="False" \
  c2p-api:latest
```

### 2. Frontend Dockerfile (Recommended Production Structure)
For frontend containerization, we recommend a multi-stage Docker build:
```dockerfile
# Stage 1: Build
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

# Stage 2: Serve
FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

---

## 🗄️ Production Database Migrations

During deployments, run migrations as part of the **release phase** (before new application containers boot up) to prevent race conditions or database locks on active instances.

1. **Isolation:** Do not run migrations inside application startups.
2. **Execution command:**
   ```bash
   alembic upgrade head
   ```
3. **Backup:** Always trigger an automated snapshot of the production database before applying any schema migrations.

---

## 🛡️ Production Hardening Checklist
- [ ] **HTTPS Enforced:** Front both application segments with SSL/TLS (certificates renewed automatically via Let's Encrypt or ACM).
- [ ] **CORS Configuration:** Configure backend CORS settings in `app/main.py` to allow only your production frontend domain (disable `allow_origins=["*"]`).
- [ ] **Secure Storage:** Uploads must be stored in a durable, isolated, and encrypted storage bucket (e.g., AWS S3, Google Cloud Storage) rather than the local container disk.
- [ ] **Token Expiry Tuning:** Reduce production `ACCESS_TOKEN_EXPIRE_MINUTES` to `60` minutes (currently set to 30 days for local development convenience).
- [ ] **Rate Limiting:** Place backend routes behind a rate-limiting proxy (e.g., Cloudflare, Nginx Rate Limit, or FastAPI Limiter) to prevent brute-force login attacks.
