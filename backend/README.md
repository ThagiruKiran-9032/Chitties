# Chitties Backend API

Enterprise Multi-Tenant Chit Fund Management Application Backend.

## Stack
- **Python**: 3.14+
- **Framework**: FastAPI
- **Server**: Uvicorn
- **ORM**: SQLAlchemy 2.x
- **Migrations**: Alembic
- **Database**: PostgreSQL 18
- **Validation**: Pydantic V2 / Pydantic-Settings
- **Testing**: Pytest & HTTPX

## Setup & Running Locally

1. Create and activate virtual environment:
   ```bash
   py -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Ensure PostgreSQL is running and credentials in `.env` match:
   ```env
   DATABASE_URL="postgresql+psycopg2://postgres:<password>@localhost:5432/chitties_db"
   ```

4. Run migrations:
   ```bash
   alembic -c alembic.ini current
   ```

5. Start the development server:
   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

6. Open interactive API docs:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`

7. Run tests:
   ```bash
   pytest -v tests
   ```
