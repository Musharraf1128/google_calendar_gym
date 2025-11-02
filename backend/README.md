# Google Calendar Gym - Backend

FastAPI backend for the Google Calendar Gym project with comprehensive calendar management, event propagation, reminders, and RL environment.

## Features

- 🔐 **ACL Management** - Role-based access control with hierarchy
- 📅 **Event Propagation** - Google Calendar-like event sharing
- ⏰ **Reminder System** - APScheduler-based notifications
- 🤖 **RL Gym Environment** - OpenAI Gym-compatible interface
- 🔄 **Recurring Events** - Full RRULE support
- 📊 **Comprehensive API** - RESTful endpoints with Swagger docs

## Quick Start

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt

# Run server
uvicorn app.main:app --reload --port 8000
```

Visit: **http://localhost:8000/docs** for API documentation

## Project Structure

```
backend/
├── app/
│   ├── gym/                 # RL environment
│   │   ├── __init__.py
│   │   └── google_calendar_env.py
│   ├── models/              # Database models
│   │   ├── models.py        # Core models
│   │   └── gym_models.py    # Legacy models
│   ├── routers/             # API endpoints
│   │   ├── calendars.py
│   │   ├── events.py
│   │   ├── users.py
│   │   └── gym.py           # RL endpoints
│   ├── services/            # Business logic
│   │   ├── acl_service.py
│   │   ├── event_service.py
│   │   └── reminder_service.py
│   ├── schemas/             # Pydantic schemas
│   ├── utils/               # Utilities
│   │   └── recurrence.py    # RRULE handling
│   ├── db.py               # Database config
│   └── main.py             # App entry point
├── tests/                   # Test suite
│   ├── test_acl.py
│   ├── test_gym.py
│   ├── test_propagation.py
│   ├── test_recurrence.py
│   └── test_reminders.py
└── requirements.txt         # Dependencies
```

## Database Models

### Core Models
- **User** - System users
- **Calendar** - User calendars
- **Event** - Calendar events
- **EventAttendee** - Event participants
- **CalendarACL** - Access control
- **CalendarListEntry** - User-calendar associations
- **Reminder** - Event reminders
- **NotificationLog** - Reminder logs

### Enums
- **CalendarRole** - owner, writer, reader, freeBusyReader
- **AttendeeResponseStatus** - accepted, declined, tentative, needsAction
- **EventStatus** - confirmed, tentative, cancelled
- **ReminderMethod** - email, popup

## Services

### ACL Service (`acl_service.py`)
```python
from app.services.acl_service import check_permission

# Check if user has permission
has_permission = check_permission(
    db, user_id, calendar_id, CalendarRole.WRITER
)
```

**Functions:**
- `check_permission()` - Verify user permissions
- `get_user_role()` - Get user's role
- `has_role_or_higher()` - Check role level

### Event Service (`event_service.py`)
```python
from app.services.event_service import create_event

# Create event with attendees
event = create_event(
    db, calendar_id, organizer_email, {
        "summary": "Meeting",
        "start": datetime.now(),
        "end": datetime.now() + timedelta(hours=1),
        "attendees": [{"email": "user@example.com"}]
    }
)
```

**Functions:**
- `create_event()` - Create with attendee copies
- `update_event()` - Update with propagation
- `update_attendee_response()` - Update response status
- `get_all_event_copies()` - Get linked events

### Reminder Service (`reminder_service.py`)
```python
from app.services.reminder_service import schedule_reminders

# Schedule reminders for an event
schedule_reminders(db, event, test_mode=False)
```

**Functions:**
- `schedule_reminders()` - Schedule with APScheduler
- `set_event_reminders()` - Set custom reminders
- `cancel_event_reminders()` - Cancel scheduled
- `get_notification_logs()` - Query logs

## API Endpoints

### Users
- `GET /api/users` - List all users
- `POST /api/users` - Create user
- `GET /api/users/{id}` - Get user
- `GET /api/users/{id}/calendars` - Get user's calendars

### Calendars
- `GET /api/calendars` - List calendars
- `POST /api/calendars` - Create calendar
- `GET /api/calendars/{id}` - Get calendar
- `GET /api/calendars/{id}/events` - List events

### Events
- `POST /api/calendars/{id}/events` - Create event
- `GET /api/events/{id}` - Get event
- `PATCH /api/events/{id}` - Update event
- `DELETE /api/events/{id}` - Delete event
- `GET /api/events/{id}/attendees` - List attendees
- `POST /api/events/{id}/reminders` - Set reminders

### Gym Environment
- `POST /api/gym/reset` - Reset environment
- `POST /api/gym/step` - Execute action
- `GET /api/gym/info` - Environment info
- `GET /api/gym/render/{id}` - Render state
- `GET /api/gym/list` - List environments
- `DELETE /api/gym/close/{id}` - Close environment

## Testing

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_acl.py -v

# Run with coverage
pytest --cov=app tests/

# Run specific test class
pytest tests/test_gym.py::TestActionSequences -v
```

### Test Coverage
- **test_acl.py** - 25 tests for ACL and permissions
- **test_gym.py** - 21 tests for RL environment
- **test_propagation.py** - 26 tests for event propagation
- **test_recurrence.py** - Tests for recurring events
- **test_reminders.py** - 20 tests for reminder system

## Configuration

### Environment Variables (`.env` in root)
```env
DATABASE_URL=sqlite:///./backend/gym_calendar.db
```

### Database
Default: SQLite (`gym_calendar.db`)

For PostgreSQL:
```env
DATABASE_URL=postgresql://user:pass@localhost/calendar_db
```

## Development

### Adding a New Endpoint
1. Create route in `app/routers/`
2. Add business logic in `app/services/`
3. Add tests in `tests/`
4. Update API docs (automatic)

### Adding a Model
1. Define in `app/models/models.py`
2. Run migrations: `alembic revision --autogenerate`
3. Apply: `alembic upgrade head`

## Dependencies

```
fastapi==0.120.4
sqlalchemy==2.0.44
pydantic==2.12.3
uvicorn==0.38.0
apscheduler==3.11.1
python-dateutil==2.9.0.post0
pytest==8.4.2
```

## Troubleshooting

**Import errors:**
```bash
# Make sure you're in the right directory
cd backend
python -m pytest tests/
```

**Database locked:**
```bash
# Close all connections or delete database
rm gym_calendar.db
```

**Port in use:**
```bash
# Use different port
uvicorn app.main:app --port 8001
```

## License

Part of the Google Calendar Gym project.
