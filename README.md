# DocumentIQ 🧠📄

DocumentIQ is a high-performance, full-stack document intelligence platform. It provides a secure user registration and authentication flow, featuring a premium dashboard for analyzing documents using simulated AI insights extraction.

## Features

- **Secure JWT Authentication**: Backend hashing (`bcrypt`) and protected endpoint session validation.
- **Modern React Frontend**: Styled with Tailwind CSS , dynamic layouts, context state management, React Router routing guards.
- **FastAPI backend**: Fast, clean Pydantic schema validation, SQLAlchemy modeling, PostgreSQL storage.
- **Docker Ready**: Preconfigured `docker-compose.yml` to orchestrate web, database, and backend systems in one command.

---

## Folder Structure

```
.
├── backend/                  # FastAPI Application
│   ├── app/
│   │   ├── api/              # Route handlers (auth, users)
│   │   ├── core/             # DB sessions, security, config
│   │   ├── models/           # SQLAlchemy models
│   │   ├── schemas/          # Pydantic validation schemas
│   │   └── main.py           # Application Entrypoint
│   ├── Dockerfile
│   ├── requirements.txt      # Dependencies
│   └── .env                  # Environment configurations
├── frontend/                 # Vite & React Application
│   ├── src/
│   │   ├── components/       # Layouts, guards
│   │   ├── context/          # Global Auth Provider
│   │   ├── pages/            # Login, Register, Dashboard
│   │   ├── App.jsx           # Main client router
│   │   └── index.css         # Tailwind directives
│   ├── Dockerfile
│   ├── nginx.conf            # Nginx config for client routing support
│   └── .env                  # Environment configurations
├── docker-compose.yml        # Infrastructure setup
└── README.md                 # Project guide
```

---

## Tech Stack

| Category | Technologies |
|----------|--------------|
| Frontend | React, Vite, Tailwind CSS v4, React Router |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | PostgreSQL |
| Authentication | JWT, bcrypt |
| DevOps | Docker, Docker Compose, Nginx |
| Language | Python, JavaScript |

## How to Run

### Method 1: Using Docker (Recommended)

1. Ensure you have Docker and Docker Compose installed.
2. In the project root, run:
   ```bash
   docker compose up --build
   ```
3. The frontend is accessible at [http://localhost:3000](http://localhost:3000).
4. The backend API is accessible at [http://localhost:8000](http://localhost:8000).
5. The API docs (Swagger UI) are available at [http://localhost:8000/docs](http://localhost:8000/docs).

### Method 2: Running Locally

#### 1. Running the Backend:
```bash
cd backend
# Create virtual env
python -m venv venv
source venv/bin/activate  # On Windows use: venv\Scripts\activate
# Install dependencies
pip install -r requirements.txt
# Run local dev server
uvicorn app.main:app --reload
```
*(Make sure to update backend `.env` `DATABASE_URL` if not running inside Docker).*

#### 2. Run the Frontend:
```bash
cd frontend
# Install packages
npm install
# Run development build
npm run dev
```
Accessible at the local dev address printed in the console (usually [http://localhost:3000](http://localhost:3000)).
