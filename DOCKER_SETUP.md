# Docker Setup Guide

## Quick Start with Docker

### Prerequisites
- Docker installed (version 20.10+)
- Docker Compose installed (version 2.0+)

### Option 1: Using Docker Compose (Recommended)

```bash
# Clone the repository
git clone <repository-url>
cd google_calendar_gym

# Start all services
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

The application will automatically:
1. Build both backend and frontend containers
2. Run database migrations
3. Seed the database with sample data
4. Start the backend API server
5. Build and serve the frontend

### Option 2: Manual Docker Build

#### Backend

```bash
cd backend

# Build the image
docker build -t calendar-gym-backend .

# Run the container
docker run -d \
  -p 8000:8000 \
  -e DATABASE_URL=sqlite:///./gym_calendar.db \
  -e UI_REALISM=true \
  --name calendar-gym-backend \
  calendar-gym-backend
```

#### Frontend

```bash
cd frontend

# Build the image
docker build -t calendar-gym-frontend .

# Run the container
docker run -d \
  -p 5173:5173 \
  -e VITE_API_BASE_URL=http://localhost:8000/api \
  --name calendar-gym-frontend \
  calendar-gym-frontend
```

## Stopping the Application

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clears database)
docker-compose down -v
```

## Troubleshooting

### Port Already in Use

```bash
# Change ports in docker-compose.yml
# For backend: "8001:8000"
# For frontend: "5174:5173"
```

### Database Not Seeded

```bash
# Restart the backend container
docker-compose restart backend

# Or manually seed
docker-compose exec backend python scripts/seed_data.py
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f frontend
```

### Rebuild After Code Changes

```bash
# Rebuild and restart
docker-compose up --build

# Rebuild specific service
docker-compose up --build backend
```

## Production Deployment

For production, consider:

1. **Use environment-specific compose files:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up
   ```

2. **Use PostgreSQL instead of SQLite:**
   - Add PostgreSQL service to docker-compose.yml
   - Update DATABASE_URL environment variable

3. **Enable HTTPS:**
   - Add nginx reverse proxy
   - Configure SSL certificates

4. **Optimize images:**
   - Use multi-stage builds
   - Minimize layer count
   - Use .dockerignore effectively

## Health Checks

The backend includes a health check endpoint:
```bash
curl http://localhost:8000/health
```

Docker Compose will automatically wait for the backend to be healthy before starting the frontend.

## Data Persistence

Database and data are persisted using Docker volumes:
- `./backend/gym_calendar.db` - SQLite database
- `./backend/data` - Screenshot dataset

To reset data:
```bash
docker-compose down -v
rm backend/gym_calendar.db
docker-compose up
```

## Resource Limits

To set resource limits, add to docker-compose.yml:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 1G
        reservations:
          memory: 512M
```

## Development vs Production

**Development (docker-compose.yml):**
- Uses source code volumes for hot reload
- Exposes all ports
- Includes debugging tools

**Production:**
- Built images only (no source mounts)
- Minimal exposed ports
- Optimized builds
- Health checks enabled
- Resource limits configured

## Verification

After starting with Docker:

1. **Check containers are running:**
   ```bash
   docker-compose ps
   ```

2. **Verify backend health:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check database has data:**
   ```bash
   docker-compose exec backend python -c "from app.db import get_db; from app.models.models import User; db = next(get_db()); print(f'Users: {len(db.query(User).all())}')"
   ```

4. **Open frontend:**
   ```
   http://localhost:5173
   ```

## Support

For issues with Docker setup:
- Check logs: `docker-compose logs`
- Verify ports are free: `lsof -i :8000` and `lsof -i :5173`
- Ensure Docker daemon is running: `docker ps`
- Check Docker Compose version: `docker-compose --version`
