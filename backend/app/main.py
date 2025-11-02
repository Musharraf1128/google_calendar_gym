from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import calendars, events, users, gym, tasks
from app.db import engine
from app.models import Base

app = FastAPI(
    title="Google Calendar Gym API",
    description="API for managing gym schedules with Google Calendar integration",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create database tables
Base.metadata.create_all(bind=engine)

# Include routers
app.include_router(users.router, prefix="/api", tags=["users"])
app.include_router(calendars.router, prefix="/api", tags=["calendars"])
app.include_router(events.router, prefix="/api", tags=["events"])
app.include_router(tasks.router, prefix="/api", tags=["tasks"])
app.include_router(gym.router, prefix="/api", tags=["gym"])


@app.get("/")
async def root():
    return {"message": "Welcome to Google Calendar Gym API"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}
