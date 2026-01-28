# AGENTS.md

This file provides guidelines and commands for agentic coding assistants working in this repository.

## Build/Lint/Test Commands

### Running the Application
```bash
# Development mode with hot reload
uvicorn main:app --reload

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000

# Alternative using Python directly
python main.py
```

### Database Migrations (Alembic)
```bash
# Create new migration
alembic revision --autogenerate -m "description"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Code Quality
```bash
# Format code (optional - not currently enforced)
black .

# Lint code (optional - not currently enforced)
flake8

# Run tests
pytest

# Run a single test file
pytest tests/test_specific_module.py

# Run a single test function
pytest tests/test_specific_module.py::test_specific_function

# Run tests with verbose output
pytest -v
```

### Dependency Management
```bash
# Install dependencies
pip install -r requirements.txt

# Update requirements.txt
pip freeze > requirements.txt
```

## Code Style Guidelines

### Import Organization
Imports must be organized in this order:
1. Standard library imports
2. Third-party imports
3. Local application imports (from app.*)

Example:
```python
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, ForeignKey, or_, func

from app.database.base import get_db
from app.models.bull import Bull
from app.services import bull_service
from app.schemas.bull_schema import BullSchema, BullCreate
```

### Naming Conventions
- **Variables/Functions**: snake_case (e.g., `get_bull`, `db_bull`, `search_query`)
- **Classes**: PascalCase (e.g., `Bull`, `Race`, `BullCreate`, `BullService`)
- **Constants**: UPPER_SNAKE_CASE (e.g., `MAX_LIMIT`)
- **Database tables**: lowercase with underscores (e.g., `bulls`, `races`)
- **Routes**: lowercase with underscores, plural for collections (e.g., `/bulls`, `/api/bull_performance`)

### Project Architecture
The codebase follows a layered architecture:

1. **Routes** (`app/routes/`): FastAPI route handlers, validate input/output
2. **Services** (`app/services/`): Business logic, database operations
3. **Models** (`app/models/`): SQLAlchemy ORM models
4. **Schemas** (`app/schemas/`): Pydantic schemas for validation

**Never** bypass the service layer in routes. All database operations must go through services.

### SQLAlchemy Models
- Inherit from both `Base` and `BaseModel` from `app.models.base_model`
- Define `__tablename__` explicitly
- Use type hints for all columns
- Include relationships with `relationship()` and `back_populates`
- Use `Enum` for status fields

Example:
```python
from sqlalchemy import Column, Integer, String, ForeignKey, Enum
from sqlalchemy.orm import relationship
from app.models.base_model import Base, BaseModel
import enum

class BullStatus(str, enum.Enum):
    active = "active"
    inactive = "inactive"

class Bull(Base, BaseModel):
    __tablename__ = "bulls"
    name = Column(String(100), nullable=False)
    status = Column(Enum(BullStatus), default=BullStatus.active, nullable=False)
    race_id = Column(Integer, ForeignKey("races.id"), nullable=False)

    race = relationship("Race", back_populates="bulls")
```

### Pydantic Schemas
- Use base classes: `EntityBase`, `EntityCreate`, `EntityUpdate`, `EntitySchema`
- Separate Create/Update schemas for flexibility
- Include `Config` class with Pydantic v2 settings
- Use descriptive Field() for complex fields

Example:
```python
from pydantic import BaseModel, Field

class BullBase(BaseModel):
    name: str
    status: Optional[BullStatus] = BullStatus.active

    class Config:
        from_attributes = True
        use_enum_values = True

class BullCreate(BullBase):
    pass

class BullUpdate(BullBase):
    name: Optional[str] = None
    status: Optional[BullStatus] = None

class BullSchema(BaseSchema, BullBase):
    user_id: int
```

### Type Hints
All functions must include type hints for parameters and return values:
```python
def get_bull(db: Session, bull_id: int, current_user: User) -> Optional[Bull]:
    pass

def create_bull(db: Session, bull: BullCreate, current_user: User) -> Bull:
    pass
```

### Error Handling
- Routes: Use `HTTPException` with appropriate status codes
- Services: Raise `HTTPException` for validation/permission errors
- Always wrap database operations in try-except with rollback on failure
- Log errors with context using `logging.getLogger(__name__)`

Example:
```python
try:
    db_bull = Bull(**bull.dict())
    db.add(db_bull)
    db.commit()
    db.refresh(db_bull)
    return db_bull
except Exception as e:
    db.rollback()
    logger.error(f"Error creating bull: {str(e)}")
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=f"Error creating bull: {str(e)}"
    )
```

### Route Handler Pattern
- Use async/await for all route handlers
- Inject database session via `Depends(get_db)`
- Inject current user via `Depends(get_current_user_from_token)`
- Return response models or `List[ResponseModel]`
- Use Query for optional parameters with validation

Example:
```python
@router.get("/", response_model=List[BullSchema])
async def get_bulls(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user_from_token)
):
    return bull_service.get_bulls(db, current_user, skip=skip, limit=limit)
```

### Database Queries
- Use SQLAlchemy ORM, not raw SQL
- Prefer `joinedload()` for eager loading relationships
- Use `func.lower()` for case-insensitive searches
- Use `or_()`, `and_()` for complex conditions
- Always apply pagination with `offset()` and `limit()`

### Authentication & Authorization
- All routes except `/auth/login`, `/auth/register` require authentication
- Use `get_current_user_from_token` dependency for authentication
- Use `role_service.is_admin()` for admin checks
- Users can only access their own resources unless they're admins

### Documentation
- Use docstrings (Spanish) for all route handlers, services, and models
- Include parameter descriptions in docstrings
- Document access restrictions in route docstrings

### Logging
- Use `logging.getLogger(__name__)` for module-level loggers
- Log errors with context (entity IDs, user IDs, etc.)
- Log info for important actions (creation, updates, deletions)

### Environment Configuration
- Use pydantic-settings for configuration (`app/config.py`)
- All sensitive data must be in `.env` file
- Never commit `.env` or secrets to git

### Testing
- Test files should be named `test_*.py` and placed in a `tests/` directory
- Use pytest for testing
- Use fixtures for database sessions and test data
- Test both success and error paths

## Cursor/Kluster Integration
This repository uses kluster code verification. After making changes:
1. Run automatic code review when requested
2. Check for dependency changes before modifying requirements.txt
3. Follow all kluster feedback and fix issues before proceeding

## Windows-Specific Notes
- The project uses `asyncio.WindowsProactorEventLoopPolicy` on Windows for Playwright support
- This is configured in `main.py` - do not modify unless necessary
