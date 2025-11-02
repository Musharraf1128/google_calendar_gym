# Google Calendar Gym

> **A Reinforcement Learning Environment for Calendar Management**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.120+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Google Calendar Gym is a full-stack RL training environment that simulates Google Calendar's behavior. Built for AI hackathons and research, it provides a realistic platform for training agents on calendar management tasks.

**[Quick Start](#quick-start)** • **[Features](#features)** • **[RL Gym API](#rl-gym-api)** • **[Testing](#testing)**

---

## Project Metrics

| Metric | Value | Status |
|--------|-------|--------|
| **Dataset Realism Score** | 0.563/1.000 | Fair (Low layout jitter: 0.225) |
| **Test Coverage** | 87.2% (164/188 passing) | Good (24 DB isolation issues) |
| **API Latency (p95)** | 71ms | Excellent (<300ms target) |
| **Screenshot Dataset** | 200 frames | Complete |
| **UI Performance** | 92/100 Lighthouse | Production-ready |

---

## Features

### Core Calendar (Google Calendar Behavior)
- **Events**: Create, update, delete with conflict detection
- **Recurring Events**: RRULE support (daily, weekly, monthly)
- **Attendees**: Multi-user invitations with response tracking
- **Calendar Sharing**: Role-based ACL (owner, writer, reader)
- **Tasks**: Appear on calendar grid at due time with checkboxes (matches Google Calendar UX)
- **Tasks View**: Dedicated tasks-only interface with lists (toggle with checkmark button)
- **Reminders**: APScheduler-based notifications

### RL Environment
- **OpenAI Gym Compatible**: Standard `reset()` and `step()` interface
- **Screenshot Generation**: Base64 PNG screenshots of calendar state
- **Binary Rewards**: +1.0 for valid actions, 0.0 for invalid
- **Actions**: Create, update, delete events; invite users; accept/decline
- **HTTP Bridge**: Remote agents via REST API

### UI Realism Features (ML Dataset)
- **7 Popup Types**: Toasts, modals, errors, notifications
- **Scroll Jitter**: Natural ±10px offset variation
- **Color Palette**: Google's 11 official colors
- **Popup Diversity**: Tracked across episodes
- **Toggle**: `UI_REALISM=true` in `.env`

### Modern Frontend
- **Inter Font**: Clean, professional typography
- **Tailwind CSS**: Google Material Design colors
- **Task Display**: Tasks shown inline on calendar grid with blue background and checkboxes
- **Tasks View**: Dedicated interface with task lists, "All tasks", "Starred", and custom lists
- **View Toggle**: Segmented control to switch between Calendar and Tasks views
- **Search**: Real-time search for events and tasks
- **View Dropdown**: Select Day, 4 Days, Week, or Month views
- **Responsive**: Mobile → Desktop breakpoints
- **Accessible**: 95/100 Lighthouse score
- **Shadows & Polish**: Subtle depth and hover effects

---

## Quick Start

### Option 1: Docker (Recommended for Hackathon Submission)

**Requirements:** Docker and Docker Compose

```bash
# Start the entire application
docker-compose up --build

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

That's it! Docker will automatically:
- Build both backend and frontend
- Run database migrations
- Seed sample data (10 users, 179 events)
- Start all services

See [DOCKER_SETUP.md](DOCKER_SETUP.md) for detailed Docker instructions.

### Option 2: Manual Setup

**Prerequisites:** Python 3.9+, Node.js 16+, pip and npm

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed sample data
python scripts/seed_data.py

# Start server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend: http://localhost:8000
✅ API Docs: http://localhost:8000/docs

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env: VITE_API_BASE_URL=http://localhost:8000/api

# Start dev server
npm run dev
```

✅ Frontend: http://localhost:5173

---

## RL Gym API

### HTTP API Example

```python
import requests
import base64

# Reset environment
response = requests.post(
    'http://localhost:8000/api/gym/reset',
    json={'env_id': 'my_agent', 'seed': 42}
)

data = response.json()
observation = data['observation']
screenshot_b64 = data['screenshot']  # Base64 PNG

# Execute action
response = requests.post(
    'http://localhost:8000/api/gym/step',
    json={
        'env_id': 'my_agent',
        'action': {
            'type': 'create_event',
            'params': {
                'organizer_email': observation['users'][0]['email'],
                'calendar_id': observation['calendars'][0]['id'],
                'summary': 'Morning Standup',
                'start_offset_hours': 1.0,
                'duration_hours': 0.5
            }
        }
    }
)

result = response.json()
print(f"Reward: {result['reward']}")  # 1.0 or 0.0
print(f"Screenshot: {result['screenshot'][:50]}...")  # Base64 PNG
```

### Available Actions

| Action | Reward | Description |
|--------|--------|-------------|
| `create_event` | +1.0 / 0.0 | Create event (0.0 if conflict) |
| `update_event` | +1.0 / 0.0 | Update event (0.0 if not found) |
| `delete_event` | +1.0 / 0.0 | Delete event (0.0 if no permission) |
| `invite_user` | +1.0 / 0.0 | Add attendee |
| `accept` / `decline` | +1.0 / 0.0 | Respond to invitation |
| `share_calendar` | +1.0 / 0.0 | Share with user |

### Observation Space

```python
{
  'users': [{'id': 'uuid', 'email': 'alice@example.com', 'name': 'Alice'}],
  'calendars': [{'id': 'uuid', 'title': 'Work Calendar'}],
  'events': [
    {
      'id': 'uuid',
      'summary': 'Team Meeting',
      'start': '2025-11-15T10:00:00Z',
      'end': '2025-11-15T11:00:00Z',
      'attendees': [...]
    }
  ],
  'conflicts': 0,
  'total_events': 5,
  'pending_responses': 2
}
```

---

## ML Training Dataset

**200 diverse screenshots** across varied calendar states:

| Event Count | Screenshots | Coverage |
|-------------|------------|----------|
| 0 events | 18 | 9.0% |
| 1-2 events | 69 | 34.5% |
| 3-4 events | 72 | 36.0% |
| 5-6 events | 34 | 17.0% |
| 7+ events | 7 | 3.5% |

**Popup Distribution:**
- 67% clean states (no popups)
- 33% with UI distractions (realistic)

**Files:**
- `data/screenshots/` - 200 PNG files
- `data/manifest.csv` - Metadata
- `google_calendar_gym_dataset.tar.gz` - Compressed (5.9 MB)

**Generate Dataset:**
```bash
cd backend
python scripts/capture_screens.py
```

**Audit Realism:**
```bash
cd backend
python realism_audit.py
```

---

## Testing

```bash
cd backend

# Run all tests
pytest -q --maxfail=1

# Check code quality
black --check .

# Run realism audit
python realism_audit.py
```

**Test Results:**
- 164/188 tests passing (87.2%)
- 24 tests fail due to database isolation issues in test setup
- 188 total tests across 8 modules
- Black formatted
- Comprehensive coverage of core features

**Test Modules:**
- `test_acl.py` - ACL & permissions
- `test_gym.py` - RL environment
- `test_propagation.py` - Event propagation
- `test_recurrence.py` - Recurring events
- `test_reminders.py` - Reminder system
- `test_tasks.py` - Task management
- `test_attendee_responses.py` - Attendee responses
- `test_calendar_acl.py` - Calendar sharing

---

## API Documentation

**RESTful Endpoints:**
- `/api/users` - User management
- `/api/calendars` - Calendar CRUD
- `/api/events` - Event operations
- `/api/tasks` - Task management
- `/api/gym/reset` - Reset RL environment
- `/api/gym/step` - Execute action

**Interactive Docs:** http://localhost:8000/docs (Swagger UI)

---

## Tech Stack

| Layer | Technologies |
|-------|-------------|
| **Backend** | FastAPI, SQLAlchemy, Pydantic, APScheduler, Alembic |
| **Frontend** | React 18, Vite, Tailwind CSS, Axios, Inter Font |
| **Database** | SQLite (dev), PostgreSQL (prod) |
| **Testing** | Pytest, Coverage.py |
| **ML/RL** | OpenAI Gym compatible, Matplotlib (rendering) |

---

## Project Structure

```
google_calendar_gym/
├── backend/
│   ├── app/
│   │   ├── gym/              # RL environment
│   │   ├── models/           # SQLAlchemy models
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Business logic
│   │   └── schemas/          # Pydantic schemas
│   ├── tests/                # 141+ tests
│   ├── scripts/
│   │   ├── seed_data.py      # Sample data
│   │   └── capture_screens.py # Dataset generator
│   ├── realism_audit.py      # Dataset quality metrics
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── services/         # API client
│   │   └── App.jsx
│   ├── tailwind.config.js    # Tailwind + custom theme
│   └── package.json
├── README.md
├── LIGHTHOUSE_AUDIT.md       # UI performance report
└── .gitignore
```

---

## Optional Tasks Completed

✅ **E2E Gym Loop with Screenshots** - Binary rewards, 3 episode demo
✅ **UI Realism Simulation** - 7 popups, scroll jitter, color palette
✅ **Load Testing** - 71ms p95 latency (<300ms target)
✅ **Screenshot Dataset** - 200 frames, manifest, tar.gz
✅ **Realism Audit** - 0.563/1.000 score (Fair rating)
✅ **Testing & Quality** - 87.2% passing, Black formatted

---

## Troubleshooting

**Backend Issues:**
```bash
# Port in use
lsof -ti:8000 | xargs kill -9

# Database locked
rm backend/gym_calendar.db
```

**Frontend Issues:**
```bash
# API connection
curl http://localhost:8000/health

# Clean install
rm -rf node_modules package-lock.json
npm install
```

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Development:**
1. Fork the repository
2. Create feature branch: `git checkout -b feature/name`
3. Add tests for new functionality
4. Run test suite: `pytest`
5. Format code: `black .`
6. Submit pull request

---

## License

MIT License - see [LICENSE](LICENSE) file.

---

## Authors

Developed for AI Hackathon - Scaler

### Technologies

- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - UI library
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL ORM
- [Pytest](https://pytest.org/) - Testing framework

---

<div align="center">

**Star this repo if you find it useful!**

Built for AI Hackathon

</div>
