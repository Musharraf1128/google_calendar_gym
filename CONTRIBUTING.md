# Contributing to Google Calendar Gym

Thank you for your interest in contributing to Google Calendar Gym! We welcome contributions from the community and are excited to have you join us.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Setup](#development-setup)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Issue Reporting](#issue-reporting)

---

## Code of Conduct

This project and everyone participating in it is governed by our commitment to creating a welcoming and inclusive environment. By participating, you are expected to:

- Use welcoming and inclusive language
- Be respectful of differing viewpoints and experiences
- Gracefully accept constructive criticism
- Focus on what is best for the community
- Show empathy towards other community members

---

## Getting Started

Before you begin:
- Read the [README.md](README.md) to understand the project
- Check the [existing issues](https://github.com/yourusername/google-calendar-gym/issues) to see if your idea or bug has already been reported
- Join discussions in the [GitHub Discussions](https://github.com/yourusername/google-calendar-gym/discussions) if you want to propose new features

---

## How to Contribute

There are many ways to contribute to Google Calendar Gym:

### Report Bugs
Found a bug? Please create an issue with:
- Clear description of the bug
- Steps to reproduce
- Expected vs. actual behavior
- Screenshots (if applicable)
- Environment details (OS, Python version, Node version)

### Suggest Enhancements
Have an idea? Create an issue with:
- Clear description of the enhancement
- Use cases and benefits
- Possible implementation approach

### Improve Documentation
- Fix typos or unclear explanations
- Add code examples
- Improve API documentation
- Write tutorials or guides

### Write Code
- Fix bugs
- Implement new features
- Improve performance
- Add tests

---

## Development Setup

### Backend Setup

```bash
# Clone repository
git clone https://github.com/yourusername/google-calendar-gym.git
cd google-calendar-gym/backend

# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install black pytest-cov pylint

# Run tests to verify setup
pytest
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Install development tools
npm install --save-dev eslint prettier

# Run development server
npm run dev
```

---

## Coding Standards

### Backend (Python)

**Style Guide:** Follow [PEP 8](https://pep8.org/)

```bash
# Format code with Black
black app/ tests/

# Run linter
pylint app/

# Type checking (optional)
mypy app/
```

**Key Conventions:**
- Use type hints for function parameters and return values
- Write docstrings for all public functions/classes (Google style)
- Keep functions small and focused
- Use meaningful variable names
- Add comments for complex logic

**Example:**
```python
def create_event(
    db: Session,
    calendar_id: UUID,
    event_data: EventCreate
) -> Event:
    """
    Create a new calendar event with attendee propagation.

    Args:
        db: Database session
        calendar_id: UUID of the calendar
        event_data: Event creation data

    Returns:
        Created event object

    Raises:
        ValueError: If calendar not found
    """
    # Implementation...
```

### Frontend (JavaScript/React)

**Style Guide:** Follow [Airbnb JavaScript Style Guide](https://github.com/airbnb/javascript)

```bash
# Format code with Prettier
npm run format

# Run linter
npm run lint
```

**Key Conventions:**
- Use functional components with hooks
- Destructure props and state
- Use meaningful component and variable names
- Keep components small and reusable
- Add JSDoc comments for complex functions

**Example:**
```jsx
/**
 * EventCard displays a single calendar event.
 *
 * @param {Object} props - Component props
 * @param {Object} props.event - Event data object
 * @param {Function} props.onClick - Click handler
 * @returns {JSX.Element}
 */
function EventCard({ event, onClick }) {
  const handleClick = (e) => {
    e.stopPropagation();
    onClick(event);
  };

  return (
    <div onClick={handleClick} className="event-card">
      {event.summary}
    </div>
  );
}
```

---

## Testing

### Backend Tests

**Write tests for:**
- All new features
- Bug fixes
- Edge cases
- API endpoints

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html tests/

# Run specific test file
pytest tests/test_tasks.py -v

# Run specific test
pytest tests/test_tasks.py::TestTaskCreation::test_create_standalone_task
```

**Test Structure:**
```python
import pytest
from app.models.models import Task, TaskStatus

class TestTaskCreation:
    """Test suite for task creation."""

    def test_create_standalone_task(self, db, test_user):
        """Test creating a task without an event."""
        # Arrange
        task_data = {
            "user_id": test_user.id,
            "title": "Buy groceries",
            "status": TaskStatus.NEEDS_ACTION
        }

        # Act
        response = client.post("/api/tasks", json=task_data)

        # Assert
        assert response.status_code == 201
        assert response.json()["title"] == "Buy groceries"
```

### Frontend Tests

```bash
# Run tests
npm test

# Run with coverage
npm run test:coverage
```

---

## Pull Request Process

### 1. Fork and Clone
```bash
# Fork via GitHub UI, then:
git clone https://github.com/YOUR_USERNAME/google-calendar-gym.git
cd google-calendar-gym
```

### 2. Create a Branch
```bash
# Create feature branch
git checkout -b feature/task-due-date-reminder

# Or bug fix branch
git checkout -b fix/timezone-conversion-bug
```

**Branch Naming:**
- `feature/` - New features
- `fix/` - Bug fixes
- `docs/` - Documentation updates
- `refactor/` - Code refactoring
- `test/` - Adding tests

### 3. Make Changes
- Write clean, well-documented code
- Follow coding standards
- Add tests for new functionality
- Update documentation as needed

### 4. Commit Changes
```bash
# Stage changes
git add .

# Commit with descriptive message
git commit -m "feat: Add due date reminder for tasks

- Add reminder_time field to Task model
- Implement APScheduler job for task reminders
- Add tests for reminder scheduling
- Update API documentation"
```

**Commit Message Format:**
```
<type>: <short summary>

<detailed description>
<list of changes>

Closes #<issue_number>
```

**Types:**
- `feat:` - New feature
- `fix:` - Bug fix
- `docs:` - Documentation changes
- `test:` - Adding tests
- `refactor:` - Code refactoring
- `style:` - Formatting, missing semicolons, etc.
- `perf:` - Performance improvements

### 5. Run Tests
```bash
# Backend
cd backend
pytest

# Frontend
cd frontend
npm test
```

### 6. Push Changes
```bash
git push origin feature/task-due-date-reminder
```

### 7. Create Pull Request

On GitHub:
1. Navigate to your fork
2. Click "New Pull Request"
3. Select your branch
4. Fill in the PR template:

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Documentation update
- [ ] Refactoring

## Testing
- [ ] Tests pass locally
- [ ] Added new tests
- [ ] Manual testing completed

## Screenshots (if applicable)
[Add screenshots]

## Related Issues
Closes #123
```

### 8. Address Review Comments
- Respond to all review comments
- Make requested changes
- Push updates to the same branch
- Request re-review when ready

---

## Issue Reporting

### Bug Reports

**Template:**
```markdown
## Bug Description
Clear description of the bug

## Steps to Reproduce
1. Go to...
2. Click on...
3. See error...

## Expected Behavior
What should happen

## Actual Behavior
What actually happens

## Screenshots
[Add screenshots]

## Environment
- OS: [e.g., Ubuntu 22.04]
- Python version: [e.g., 3.10.5]
- Node version: [e.g., 18.12.0]
- Browser: [e.g., Chrome 120]
```

### Feature Requests

**Template:**
```markdown
## Feature Description
Clear description of the feature

## Use Case
Why is this feature needed?

## Proposed Solution
How might this be implemented?

## Alternatives Considered
Other approaches you've thought about

## Additional Context
Any other information
```

---

## Project Structure Reference

```
google_calendar_gym/
├── backend/
│   ├── app/
│   │   ├── gym/              # RL environment
│   │   ├── models/           # Database models
│   │   ├── routers/          # API endpoints
│   │   ├── services/         # Business logic
│   │   ├── schemas/          # Pydantic schemas
│   │   └── utils/            # Utility functions
│   ├── tests/                # Test suite
│   └── scripts/              # Utility scripts
├── frontend/
│   ├── src/
│   │   ├── components/       # React components
│   │   ├── services/         # API client
│   │   └── utils/            # Utility functions
│   └── tests/                # Frontend tests
└── docs/                     # Documentation
```

---

## Getting Help

- Read the [README.md](README.md)
- Ask questions in [GitHub Discussions](https://github.com/yourusername/google-calendar-gym/discussions)
- Report bugs in [Issues](https://github.com/yourusername/google-calendar-gym/issues)
- Contact maintainers (see README)

---

## Recognition

Contributors will be recognized in:
- README.md acknowledgments
- Release notes
- Project documentation

Thank you for contributing to Google Calendar Gym!

---

## Quick Reference

### Common Commands

**Backend:**
```bash
# Activate venv
source .venv/bin/activate

# Run server
uvicorn app.main:app --reload

# Run tests
pytest -v

# Format code
black app/ tests/

# Check linting
pylint app/
```

**Frontend:**
```bash
# Install deps
npm install

# Run dev server
npm run dev

# Run tests
npm test

# Format code
npm run format

# Lint code
npm run lint
```

**Git:**
```bash
# Create branch
git checkout -b feature/my-feature

# Stage changes
git add .

# Commit
git commit -m "feat: add feature"

# Push
git push origin feature/my-feature

# Update from main
git fetch origin
git rebase origin/main
```

---

**Last Updated:** November 2025
