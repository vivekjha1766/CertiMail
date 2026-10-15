# Contributing to CertiMail

Thank you for your interest in improving CertiMail! We welcome contributions to enhance reliability, streamline workflows, and add new event distribution capabilities.

---

## Code of Conduct

Please maintain professional, respectful, and constructive communication when participating in this project.

---

## Development Environment Setup

### Prerequisites
- **Python**: 3.10, 3.11, 3.12, or 3.13
- **Node.js**: 18.0 or newer
- **Git**

### 1. Fork & Clone
```bash
git clone https://github.com/<your-username>/certimailer.git
cd certimailer
```

### 2. Backend Setup
```powershell
python -m venv .venv
.\.venv\Scripts\activate   # On Linux/macOS: source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Frontend Setup
```bash
cd frontend
npm install
cd ..
```

### 4. Running the Development Servers
You can use the provided Windows startup script:
```powershell
.\start.ps1
```
Or start the servers manually in separate terminal sessions:
- Backend: `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`
- Frontend: `cd frontend && npm run dev`

---

## Testing & Quality Assurance

Before submitting any code changes, ensure all tests pass cleanly:

### 1. Run Backend Automated Tests
All 36 existing tests must pass with zero failures:
```powershell
python -m pytest backend/tests/ -v
```
When modifying or adding features, write corresponding tests in `backend/tests/` using mocked SMTP transports (`unittest.mock`) to guarantee no real emails are sent during test execution.

### 2. Verify Frontend Build & Types
Ensure TypeScript type-checking and bundling succeed with zero errors:
```bash
cd frontend
npm run build
```

---

## Code Style & Standards

- **Python (Backend)**:
  - Adhere to PEP 8 standards.
  - Use explicit type hints with Pydantic v2 schemas for all API inputs and outputs.
  - Follow the existing layered architecture (`api/`, `core/`, `schemas/`, `services/`).
  - Never commit credentials, tokens, or hardcoded passwords.
- **TypeScript / React (Frontend)**:
  - Write strict, type-safe TypeScript. Avoid using `any`.
  - Maintain component reusability and adhere to Tailwind CSS v4 styling patterns.
  - Keep state management clean and utilize `AppContext` for cross-view state.

---

## Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat:` A new feature or user-facing enhancement.
- `fix:` A bug fix.
- `docs:` Documentation changes only.
- `test:` Adding or updating automated tests.
- `refactor:` Code restructuring without changing external behavior.
- `chore:` Dependency updates, configuration, or build tool changes.

---

## Submitting Pull Requests

1. Create a descriptive feature branch:
   ```bash
   git checkout -b feat/dynamic-team-size
   ```
2. Verify that all automated tests pass and frontend builds cleanly.
3. Ensure no local SQLite databases (`*.db`), generated ZIPs, spreadsheets, or `.env` files are tracked.
4. Push your branch and open a Pull Request with a clear summary of the changes, motivation, and verification steps.
