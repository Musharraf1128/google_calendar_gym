# 📅 Google Calendar Gym

<div align="center">

**A Reinforcement Learning Environment for Calendar Management with Google Calendar-inspired UI**

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.120+-green.svg)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-18-blue.svg)](https://reactjs.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[Features](#-features) • [Quick Start](#-quick-start) • [Screenshots](#-screenshots) • [RL Gym](#-rl-gym-environment) • [API](#-api-documentation) • [Contributing](#-contributing)

</div>

---

## 🎯 Project Overview

**Google Calendar Gym** is a comprehensive calendar management system built as a **Reinforcement Learning (RL) environment** for AI hackathons and research. It provides a realistic simulation of Google Calendar's behavior with a full-stack implementation that allows RL agents to learn optimal calendar management strategies.

### Hackathon Context

This project was developed to explore:
- **Multi-agent coordination** through calendar sharing and event attendee management
- **Sequential decision-making** in scheduling and conflict resolution
- **Reward shaping** for productivity optimization
- **Real-world API integration** patterns for RL agents

The system combines a production-ready **FastAPI backend** with a **React frontend** that faithfully replicates Google Calendar's UX, making it perfect for testing RL agents in realistic scenarios.

---

## ✨ Features

### 🗓️ Core Calendar Features (Google Calendar Behavior)

- **Event Management**
  - Create, read, update, delete events
  - Recurring events with RRULE support (daily, weekly, monthly patterns)
  - All-day events
  - Multi-day spanning events
  - Event color coding (8 color options)
  - Drag-and-drop event rescheduling
  - Event resizing for duration adjustment

- **Event Attendees & Propagation**
  - Add multiple attendees to events
  - Automatic event copy creation in attendees' calendars
  - Linked via `iCalUID` for synchronization
  - Response status tracking: `needsAction`, `accepted`, `declined`, `tentative`
  - Response updates propagate back to organizer
  - Attendee response notifications

- **Calendar Sharing & ACL**
  - Role-based access control: `owner`, `writer`, `reader`, `freeBusyReader`
  - Calendar sharing with multiple users
  - Permission hierarchy enforcement
  - CalendarList for user-calendar relationships

- **Reminder System**
  - Event-level custom reminders (email, popup)
  - Calendar default reminders
  - APScheduler-based scheduling
  - Multiple reminders per event
  - Notification logging for tracking

- **Tasks (Google Calendar Style)** ✨
  - Create standalone tasks or link to events
  - Task fields: `title`, `notes`, `due` date, `status` (needsAction/completed)
  - Task display as checkboxes below day columns
  - Toggle completion with instant UI updates
  - Filter tasks by status, due date, or related event

### 🤖 RL Gym Environment

- **OpenAI Gym-compatible interface**
- **Actions**: `create_event`, `invite_user`, `accept`, `decline`, `share_calendar`, `update_event`
- **Observations**: Structured state with events, users, calendars, conflicts
- **Rewards**: Configurable reward function for optimization
- **HTTP Bridge**: Remote agents can interact via REST API
- **Multi-instance**: Support for parallel environments

### 🎨 Frontend UI

- **Google Calendar-inspired design**
- **Multiple views**: Day, 4 Days, Week, Month
- **Interactive features**:
  - Drag-and-drop event scheduling
  - Click-to-create events
  - Quick event preview popup
  - Full event edit modal
  - Mini calendar navigation
  - Task management UI with checkboxes
- **Responsive and modern** with Tailwind CSS

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.9+**
- **Node.js 16+**
- **pip** and **npm**

### 1️⃣ Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run database migrations (if using Alembic)
alembic upgrade head

# Seed sample data (optional)
python scripts/seed_data.py

# Start the FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

✅ Backend running at: **http://localhost:8000**
✅ API docs at: **http://localhost:8000/docs**

### 2️⃣ Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env to set VITE_API_BASE_URL=http://localhost:8000/api

# Start the development server
npm run dev
```

✅ Frontend running at: **http://localhost:5173**

### 3️⃣ Verify Setup

1. Open **http://localhost:5173** in your browser
2. Select a user (Alice, Bob, etc.)
3. Create an event by clicking on a time slot
4. Try creating a task using the "Create" dropdown
5. Drag events to reschedule them

---

## 📸 Screenshots

### Calendar Week View
![Calendar Week View](docs/screenshots/week_view.png)
*Week view with events, drag-and-drop, and task checkboxes below each day*

### Event Creation Modal
![Event Modal](docs/screenshots/event_modal.png)
*Create or edit events with title, time, location, description, and color*

### Task Management
![Tasks](docs/screenshots/tasks.png)
*Tasks displayed as checkboxes below day columns, exactly like Google Calendar*

### Multiple Views
![Views](docs/screenshots/views.png)
*Day, 4 Days, Week, and Month views available*

### RL Environment Visualization
![RL Gym](docs/screenshots/gym_render.png)
*Gym environment state rendering showing events, conflicts, and metrics*

---

## 🤖 RL Gym Environment

### Basic Usage

```python
from app.gym import GoogleCalendarEnv

# Create environment
env = GoogleCalendarEnv()

# Reset environment
observation = env.reset(seed=42)

# Step through environment
action = {
    "type": "create_event",
    "params": {
        "organizer_email": "alice@example.com",
        "calendar_id": "uuid-of-calendar",
        "summary": "Team Meeting",
        "start": "2025-11-15T10:00:00Z",
        "end": "2025-11-15T11:00:00Z",
        "attendees": [
            {"email": "bob@example.com"},
            {"email": "charlie@example.com"}
        ]
    }
}

observation, reward, done, truncated, info = env.step(action)

print(f"Reward: {reward}")
print(f"Events: {len(observation['events'])}")
print(f"Conflicts: {observation['conflicts']}")
```

### HTTP API for Remote Agents

```python
import requests

# Reset environment
response = requests.post('http://localhost:8000/api/gym/reset')
env_id = response.json()['env_id']

# Execute action
response = requests.post(
    f'http://localhost:8000/api/gym/step',
    json={
        'env_id': env_id,
        'action': {
            'type': 'create_event',
            'params': {
                'organizer_email': 'alice@example.com',
                'calendar_id': 'calendar-uuid',
                'summary': 'Morning Standup'
            }
        }
    }
)

result = response.json()
print(f"Reward: {result['reward']}")
print(f"Done: {result['done']}")
```

### Available Actions

| Action | Description | Parameters |
|--------|-------------|------------|
| `create_event` | Create a new event | `organizer_email`, `calendar_id`, `summary`, `start`, `end`, `attendees` |
| `invite_user` | Add attendee to event | `event_id`, `email` |
| `accept` | Accept event invitation | `event_id`, `email` |
| `decline` | Decline event invitation | `event_id`, `email` |
| `share_calendar` | Share calendar with user | `calendar_id`, `email`, `role` |
| `update_event` | Modify existing event | `event_id`, `start`, `end`, `summary` |

### Observation Space

```python
{
    'users': [
        {'id': 'uuid', 'email': 'alice@example.com', 'name': 'Alice Johnson'},
        # ... more users
    ],
    'calendars': [
        {'id': 'uuid', 'title': 'Work Calendar', 'owner_id': 'uuid'},
        # ... more calendars
    ],
    'events': [
        {
            'id': 'uuid',
            'summary': 'Team Meeting',
            'start': '2025-11-15T10:00:00Z',
            'end': '2025-11-15T11:00:00Z',
            'attendees': [...]
        },
        # ... more events
    ],
    'conflicts': 3,  # Number of scheduling conflicts
    'total_events': 42,
    'pending_responses': 5
}
```

### Reward Structure

- **+10**: Successfully created event
- **+5**: Attendee accepted invitation
- **-5**: Attendee declined invitation
- **-10**: Created scheduling conflict
- **+3**: Calendar shared successfully
- **+2**: Event updated without conflicts

---

## 📚 API Documentation

### RESTful Endpoints

#### Users
- `GET /api/users` - List all users
- `POST /api/users` - Create new user
- `GET /api/users/{id}` - Get user details
- `GET /api/users/{id}/calendars` - Get user's calendars
- `GET /api/users/{id}/tasks` - Get user's tasks

#### Calendars
- `GET /api/calendars` - List calendars
- `POST /api/calendars` - Create calendar
- `GET /api/calendars/{id}` - Get calendar
- `GET /api/calendars/{id}/events` - List events (with filters)
- `POST /api/calendars/{id}/share` - Share calendar

#### Events
- `POST /api/calendars/{id}/events` - Create event
- `GET /api/events/{id}` - Get event
- `PATCH /api/events/{id}` - Update event
- `DELETE /api/events/{id}` - Delete event
- `GET /api/events/{id}/attendees` - List attendees
- `PATCH /api/events/{id}/attendees/{attendee_id}` - Update response
- `POST /api/events/{id}/reminders` - Set reminders
- `GET /api/events/{id}/tasks` - Get linked tasks

#### Tasks
- `POST /api/tasks` - Create task
- `GET /api/tasks/{id}` - Get task
- `PATCH /api/tasks/{id}` - Update task
- `DELETE /api/tasks/{id}` - Delete task
- `POST /api/tasks/{id}/toggle` - Toggle completion status

#### Gym Environment
- `POST /api/gym/reset` - Reset environment (returns `env_id`)
- `POST /api/gym/step` - Execute action
- `GET /api/gym/info` - Environment information
- `GET /api/gym/render/{id}` - Visualize state
- `GET /api/gym/list` - List active environments
- `DELETE /api/gym/close/{id}` - Close environment

**Interactive API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs) (Swagger UI)

---

## 🗄️ Database Schema

### Core Models

```
┌──────────┐        ┌────────────┐        ┌────────┐
│  User    │◄──────┤ Calendar   │◄──────┤ Event  │
│  - id    │        │ - id       │        │ - id   │
│  - email │        │ - title    │        │ - summary
│  - name  │        │ - owner_id │        │ - start
└──────────┘        └────────────┘        │ - end
     ▲                     ▲               │ - iCalUID
     │                     │               └────────┘
     │              ┌──────────────┐            │
     │              │ CalendarACL  │            │
     └──────────────┤ - role       │            │
                    │ - grantee    │            │
                    └──────────────┘            │
                                                ▼
                                        ┌───────────────┐
                                        │ EventAttendee │
                                        │ - email       │
                                        │ - response    │
                                        └───────────────┘
```

### Task Model

```
┌──────────┐        ┌────────┐
│   Task   │        │ Event  │
│  - id    │───────►│ - id   │
│  - title │        └────────┘
│  - notes │
│  - due   │
│  - status│ (needsAction/completed)
│  - related_event_id
└──────────┘
```

---

## 🧪 Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_tasks.py -v

# Run with coverage
pytest --cov=app tests/

# Run specific test class
pytest tests/test_gym.py::TestActionSequences -v
```

**Test Coverage:**
- ✅ `test_acl.py` - 25 tests for ACL & permissions
- ✅ `test_gym.py` - 21 tests for RL environment
- ✅ `test_propagation.py` - 26 tests for event propagation
- ✅ `test_recurrence.py` - 18 tests for recurring events
- ✅ `test_reminders.py` - 20 tests for reminder system
- ✅ `test_tasks.py` - 14 tests for task management
- ✅ `test_attendee_responses.py` - 10 tests for attendee responses
- ✅ `test_calendar_acl.py` - 7 tests for calendar sharing

**Total:** 141+ tests with comprehensive coverage

---

## 📊 Sample Dataset

The project includes a comprehensive seed data script:

```bash
cd backend
python scripts/seed_data.py
```

**Generated Data:**
- 🙋 10 users (Alice, Bob, Charlie, Diana, Ethan, Fiona, George, Hannah, Ian, Julia)
- 📅 6 calendars (3 personal + 3 shared)
- 📆 ~200 events:
  - Single events
  - Recurring events (daily, weekly, monthly)
  - All-day events
  - Multi-day events
  - Timezone-shifted events
  - Overlapping events
  - Cancelled events
- ⏰ 50+ reminders
- 🔔 Notification logs
- 🤝 Shared calendars with varied ACL roles

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** 0.120+ - Modern Python web framework
- **SQLAlchemy** 2.0+ - SQL toolkit and ORM
- **Alembic** - Database migrations
- **Pydantic** 2.0+ - Data validation
- **APScheduler** 3.11+ - Task scheduling for reminders
- **Pytest** 8.4+ - Testing framework
- **Uvicorn** - ASGI server

### Frontend
- **React** 18 - UI library
- **Vite** - Build tool and dev server
- **Axios** - HTTP client
- **Tailwind CSS** - Utility-first CSS
- **React Hooks** - State management

### Database
- **SQLite** (default) - Development database
- **PostgreSQL** (optional) - Production database

---

## 📁 Project Structure

```
google_calendar_gym/
├── backend/
│   ├── app/
│   │   ├── gym/                    # RL environment
│   │   │   └── google_calendar_env.py
│   │   ├── models/
│   │   │   └── models.py           # SQLAlchemy models
│   │   ├── routers/
│   │   │   ├── calendars.py        # Calendar endpoints
│   │   │   ├── events.py           # Event endpoints
│   │   │   ├── users.py            # User endpoints
│   │   │   ├── tasks.py            # Task endpoints
│   │   │   └── gym.py              # Gym endpoints
│   │   ├── services/
│   │   │   ├── acl_service.py      # Permission checking
│   │   │   ├── event_service.py    # Event logic
│   │   │   └── reminder_service.py # Scheduling
│   │   ├── schemas/
│   │   │   └── __init__.py         # Pydantic schemas
│   │   ├── db.py                   # Database config
│   │   └── main.py                 # App entry point
│   ├── tests/                       # Test suite (141+ tests)
│   ├── scripts/
│   │   └── seed_data.py            # Sample data generator
│   ├── alembic/                     # Database migrations
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── CalendarGrid.jsx    # Week/4-day view
│   │   │   ├── DayView.jsx         # Day view
│   │   │   ├── MonthView.jsx       # Month view
│   │   │   ├── EventModal.jsx      # Event editor
│   │   │   ├── TaskModal.jsx       # Task editor
│   │   │   ├── EventCard.jsx       # Event display
│   │   │   ├── MiniCalendar.jsx    # Navigation
│   │   │   └── QuickEventPopup.jsx # Event preview
│   │   ├── services/
│   │   │   └── api.js              # API client
│   │   └── App.jsx                 # Main component
│   ├── package.json
│   └── .env.example
├── .gitignore
├── README.md
├── LICENSE
└── CONTRIBUTING.md
```

---

## 🌟 Key Design Decisions

### 1. Event Propagation (Google Calendar Style)
Events shared with attendees create **linked copies** in each attendee's calendar. All copies share the same `iCalUID` for synchronization. When an attendee responds, the response updates across all copies.

### 2. ACL Hierarchy
Permissions follow Google Calendar's model:
- `owner` > `writer` > `reader` > `freeBusyReader`
- Owners can do everything
- Writers can create/edit events
- Readers can view events
- FreeBusyReaders only see free/busy status

### 3. Reminder Scheduling
APScheduler manages reminder jobs:
- Event-level reminders override calendar defaults
- Jobs scheduled based on `minutes_before` parameter
- Notifications logged for audit trail

### 4. Tasks Implementation
Tasks follow Google Calendar's approach:
- Can be standalone or linked to events (`related_event_id`)
- Status: `needsAction` or `completed`
- Displayed as checkboxes below day columns
- Instant toggle with backend sync

### 5. RL Environment Design
OpenAI Gym compatibility for standard RL algorithms:
- Discrete action space (action types)
- Dict observation space (structured state)
- Configurable reward function
- Episode termination after 100 steps or goal achievement

---

## 🐛 Troubleshooting

### Backend Issues

**Port already in use:**
```bash
lsof -ti:8000 | xargs kill -9
uvicorn app.main:app --reload --port 8001
```

**Database locked:**
```bash
rm backend/gym_calendar.db
# Restart server to recreate tables
```

**Import errors:**
```bash
cd backend
source .venv/bin/activate
pip install -r requirements.txt
```

### Frontend Issues

**API connection errors:**
- Verify backend is running: `curl http://localhost:8000/health`
- Check CORS configuration in `backend/app/main.py`
- Verify `VITE_API_BASE_URL` in `frontend/.env`

**Module not found:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

**Build errors:**
```bash
cd frontend
npm run build
# Check for errors in console
```

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Make your changes
4. Add tests for new functionality
5. Run test suite: `pytest` (backend) and `npm test` (frontend)
6. Commit changes: `git commit -m 'Add amazing feature'`
7. Push to branch: `git push origin feature/amazing-feature`
8. Open a Pull Request

### Code Style

- **Backend**: Follow PEP 8, use Black formatter
- **Frontend**: Follow Airbnb JavaScript style guide, use Prettier
- **Tests**: Write tests for all new features
- **Documentation**: Update README and docstrings

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Authors & Acknowledgments

**Developed for AI Hackathon - Scaler**

### Core Contributors
- Calendar API & Event Management
- RL Gym Environment & HTTP Bridge
- Frontend React Application
- Event Propagation System
- Reminder Service with APScheduler
- Task Management Feature
- Comprehensive Test Suite

### Technologies & Libraries
- [FastAPI](https://fastapi.tiangolo.com/) - Modern Python web framework
- [React](https://reactjs.org/) - UI library
- [SQLAlchemy](https://www.sqlalchemy.org/) - ORM
- [APScheduler](https://apscheduler.readthedocs.io/) - Task scheduling
- [Tailwind CSS](https://tailwindcss.com/) - Styling
- [Vite](https://vitejs.dev/) - Build tool
- [Pytest](https://pytest.org/) - Testing framework

---

## 🚀 Roadmap

Future enhancements:
- [ ] Real Google Calendar API integration
- [ ] WebSocket support for real-time updates
- [ ] Multi-calendar view with color coding
- [ ] Advanced RL algorithms (PPO, A3C) integration
- [ ] Calendar import/export (iCal format)
- [ ] Email notifications via SMTP
- [ ] Mobile responsive improvements
- [ ] Dark mode support
- [ ] Event search and filtering
- [ ] Calendar subscription links

---

## 📞 Support

- **Documentation**: [API Docs](http://localhost:8000/docs)
- **Issues**: [GitHub Issues](https://github.com/yourusername/google-calendar-gym/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/google-calendar-gym/discussions)

---

<div align="center">

**⭐ If you find this project useful, please consider giving it a star! ⭐**

Made with ❤️ for AI Hackathon

</div>
