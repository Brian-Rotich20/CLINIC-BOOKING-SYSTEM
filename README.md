# Clinic Booking API

A REST API for a small clinic (5 doctors) to manage online appointment
booking — patients can view a doctor's free slots, book, cancel, or
reschedule. Built for the Savannah Informatics Backend Developer take-home
assessment.

- **Live URL:** https://clinic-booking-system-8k20.onrender.com/
- **Repo:** https://github.com/Brian-Rotich20/CLINIC-BOOKING-SYSTEM
- **API docs (Swagger UI):** https://clinic-booking-system-8k20.onrender.com/api/docs/
- **Stack:** Python · Django · Django REST Framework · PostgreSQL · Render · GitHub Actions


> Use  Swagger UI link above to explore and
> test every endpoint interactively.

---

## System Design

### The Scenario

> "We run a small clinic with 5 doctors. Patients need to book appointments
> online. Each doctor has set working hours and works in 30-minute slots. A
> patient should see which slots are free for a given doctor on a given day,
> pick one, and book it. Once booked, that slot must not be available to
> others. Patients should also be able to cancel. We're starting small but
> want to grow."

### Entities identified

- **Doctor** — a clinician with working hours
- **WorkingHours** — recurring weekly availability window per doctor (e.g. Mon–Fri 9am–5pm)
- **Patient** — the person booking
- **Appointment** — a booked (or cancelled) 30-minute slot linking a doctor + patient + time range

### Key relationships

- One Doctor → many WorkingHours entries (one per weekday)
- One Doctor → many Appointments
- One Patient → many Appointments
- A slot is "taken" only if there's a non-cancelled Appointment at that exact start time

---

## Models

### Doctor
| Field | Type | Notes |
|---|---|---|
| id | PK | |
| name | CharField | |
| specialty | CharField | optional |

### WorkingHours
| Field | Type | Notes |
|---|---|---|
| id | PK | |
| doctor | FK → Doctor | |
| weekday | IntegerField (0–6) | Mon=0 … Sun=6 |
| start_time | TimeField | |
| end_time | TimeField | |

### Patient
| Field | Type | Notes |
|---|---|---|
| id | PK | |
| name | CharField | |
| email | EmailField (unique) | |
| phone | CharField | optional |

### Appointment
| Field | Type | Notes |
|---|---|---|
| id | PK | |
| doctor | FK → Doctor | |
| patient | FK → Patient | |
| start_time | DateTimeField | timezone-aware |
| end_time | DateTimeField | start + 30 min |
| status | CharField (choices) | `booked` / `cancelled` |
| cancellation_reason | CharField, nullable | required only when cancelled |
| created_at / updated_at | DateTimeField | audit trail |

**Constraint:** a partial unique index on `(doctor, start_time)` where
`status='booked'`, enforced at the database level — not just checked in
application code — so the guarantee holds even under concurrent booking
requests.

---

## Architecture

```
clinic-booking/
├── apps/
│   ├── doctors/          # Doctor, WorkingHours, availability endpoint
│   ├── patients/         # Patient, upcoming-appointments endpoint (bonus)
│   └── appointments/     # Appointment model, services.py, booking/cancel/reschedule endpoints
├── config/                # project settings, root urls.py
├── build.sh                # Render build command: install deps, collectstatic, migrate
├── docker-compose.yml      # optional local Postgres
└── .github/workflows/ci-cd.yml
```

**Why three apps instead of one:** the brief explicitly says "we're starting
small but want to grow." Splitting `doctors`, `patients`, and `appointments`
into their own apps costs more scaffolding upfront, but lets each domain
evolve independently later (e.g. doctors gaining multi-location support,
patients gaining accounts/auth) without unrelated models sharing a file.

**Why a `services.py` layer inside `appointments`:** booking/cancel/reschedule
all share validation logic (working-hours check, past-date check, lead-time
check, slot-conflict check). Keeping this out of `views.py` makes it directly
unit-testable without spinning up the HTTP layer, and keeps views as thin
adapters between HTTP and business logic.

**Why a custom DRF exception handler:** each business rule violation
(`InvalidSlotError`, `SlotUnavailableError`, `AppointmentNotFoundError`,
`AlreadyCancelledError`) carries its own HTTP status code and maps to a
response automatically — views never need repeated try/except blocks, and
every error response has a consistent `{"detail": "..."}` shape.

---

## Design Decisions & Trade-offs

- **Three apps over one.** See Architecture above. Trade-off: more files and
  cross-app imports (`appointments` imports `Doctor` and `Patient`) for a
  3–5 day build, in exchange for cleaner long-term separation.

- **Slots are generated dynamically from `WorkingHours`,** not pre-created as
  rows. Availability = working hours minus existing booked appointments for
  that date, computed on request. Avoids a cron job to pre-populate slots and
  avoids storage bloat as the clinic scales.

- **Authentication/authorization is out of scope.** The brief doesn't mention
  login, roles, or auth endpoints, so any `patient_id`/`appointment_id`
  passed in a request is trusted as-is. In production, patients would
  authenticate and cancel/reschedule would be restricted to their own
  appointments.

- **Double-booking prevention is enforced at two layers, not one.**
  `services.py` pre-validates the slot (past/lead-time/working-hours), but
  the actual conflict guarantee is a database-level `UniqueConstraint`. The
  booking/reschedule write happens inside `transaction.atomic()`, and an
  `IntegrityError` from the constraint is caught and converted into a clean
  `SlotUnavailableError`. This matters under concurrent requests, where an
  app-level-only check could race.

- **Cancelling doesn't delete the appointment row** — it flips `status` to
  `cancelled`, which the unique constraint then ignores, freeing the slot.
  Keeps a full history for `/patients/{id}/appointments`.

- **Reschedule reuses the same slot-validation function as a fresh booking**
  (as the brief requires), rather than duplicating the logic.

- **`SlotUnavailableError` returns HTTP 409, not 400.** The brief only
  requires "correct" status codes without specifying which; 409 Conflict is
  the more accurate code for "this resource state conflicts with your
  request" than a generic 400.

- **1-hour minimum lead time (bonus requirement)** is enforced inside the
  shared slot-validation function, so it automatically applies to both fresh
  bookings and reschedules without separate logic.
 ## API Endpoints

Interactive API documentation is available at:

**Swagger UI:** https://clinic-booking-system-8k20.onrender.com/api/docs/#/

Use the **Try it out** feature to test each endpoint directly from your browser.

### Suggested Testing Flow

Sample data is already available:

- `doctor_id: 1`
- `patient_id: 1`

Test the API in this order:

1. **Check Availability**
   - `GET /doctors/{id}/availability`
   - Use `doctor_id = 1` and any upcoming Monday–Friday.

2. **Book an Appointment**
   - `POST /appointments`
   - Use one of the available slots returned in Step 1.
   - Copy the returned `appointment_id`.

3. **Cancel the Appointment**
   - `PATCH /appointments/{id}/cancel`
   - Use the `appointment_id` from Step 2 and provide a cancellation reason.

4. **Reschedule an Appointment**
   - Book another appointment, then call
     `PATCH /appointments/{id}/reschedule`
     with a new available time.

5. **View Patient Appointments**
   - `GET /patients/{id}/appointments`
   - Use `patient_id = 1` to verify the booking history.

> **Note:** If booking returns **409 Conflict**, the selected slot has already been booked. Simply choose another available slot and try again.

---

### Available Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/doctors/{id}/availability` | View available appointment slots |
| POST | `/appointments` | Book an appointment |
| PATCH | `/appointments/{id}/cancel` | Cancel an appointment |
| PATCH | `/appointments/{id}/reschedule` | Reschedule an appointment |
| GET | `/patients/{id}/appointments` | View a patient's upcoming appointments |---

## Running Locally

### 1. Clone the repository

```bash
git clone https://github.com/Brian-Rotich20/CLINIC-BOOKING-SYSTEM.git
cd CLINIC-BOOKING-SYSTEM
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv

# Linux/macOS
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Copy the example environment file and update it with your PostgreSQL credentials.

```bash
cp .env.example .env
```

Set the following variables in your `.env` file:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
DB_HOST=your_database_host
DB_PORT=5432
```

> Replace the database values with your own PostgreSQL credentials.``

### 5. Apply database migrations

```bash
python manage.py migrate
```

### 6. Create an administrator account

```bash
python manage.py createsuperuser
```

### 7. Start the development server

```bash
python manage.py runserver
```

The application will be available at:

- API: http://127.0.0.1:8000/
- Admin: http://127.0.0.1:8000/admin/

> **Note:** The project does not include seed data. After logging into the Django Admin, create at least one **Doctor**, configure their **Working Hours**, and create a **Patient** before testing the booking endpoints.

### Run the test suite
```bash
python manage.py test
```

Optional: `docker-compose up -d` to run Postgres locally instead of pointing
at a remote database.

Visit `http://127.0.0.1:8000/admin/` to add a Doctor, WorkingHours, and
Patient before testing the booking endpoints — the app has no seed data by
default.

---

## Testing

```bash
python manage.py test apps.appointments apps.doctors apps.patients
```

23 tests covering the booking logic in `services.py`:
- **Availability** — correct slots returned, booked slots excluded, cancelled
  slots freed back up, no-working-hours days return empty, 1-hour lead time
  respected
- **Booking** — happy path, and every rejection case (past, too-soon,
  outside working hours, misaligned to the 30-min grid, no working hours that
  day, double-booking)
- **Cancel/Reschedule** — happy paths, slot freed after cancel/reschedule,
  double-cancel rejected, missing reason rejected, not-found handled,
  reschedule-to-taken-slot rejected, reschedule of a cancelled appointment
  rejected, new slot re-validated like a fresh booking

Tests run against a disposable database (Django creates/destroys a separate
test DB automatically), never against production data.

---

## Deployment

- **Provider:** Render
- **Public URL:** https://clinic-booking-system-8k20.onrender.com/
- **Database:** Render-managed PostgreSQL
- **Build command:** `./build.sh` — installs dependencies, runs
  `collectstatic`, runs `migrate` on every deploy
- **Start command:** `gunicorn config.wsgi:application`
- **Static files:** served via WhiteNoise (no separate static host needed)

---

## CI/CD

- **Tool:** GitHub Actions (`.github/workflows/ci-cd.yml`)
- **On every pull request targeting `main`:** spins up a disposable
  PostgreSQL 16 service container, installs dependencies, runs migrations,
  runs the full test suite. A failing test blocks merge.
- **On merge to `main`:** the same test job runs again; if it passes, a
  second job sends a POST request to a Render deploy hook (stored as the
  `RENDER_DEPLOY_HOOK_URL` GitHub secret), triggering an automatic deploy.
  Deployment never fires if tests fail.
- **Why tests run against a real Postgres container, not SQLite:** the
  double-booking guard relies on a Postgres-specific partial unique
  constraint; testing against SQLite could pass in CI while behaving
  differently against production Postgres.

--

 ## AI Reflection

### 1. What did you use AI for?
- Discussing the system design and overall project architecture.
- Generating and refining models, serializers, views, business logic (`services.py`), custom exception handling, and test cases.
- Assisting with debugging, fixing configuration issues, and resolving deployment challenges.
- Setting up deployment, GitHub Actions CI/CD, Swagger/OpenAPI documentation, and Render configuration.
- Drafting and improving the README and other project documentation.

### 2. One example where AI improved your work
- AI suggested using both application-level validation and a database constraint to prevent double bookings.
- This improved the reliability of the booking system by reducing the risk of conflicting bookings.

### 3. One example where AI was wrong or incomplete
- AI initially focused only on configuring the CI/CD workflow.
- After reviewing the assessment requirements, I realized I also needed to create a feature branch, open a pull request, and merge it into `main` to demonstrate the complete CI/CD pipeline.
- I implemented the full Git workflow to satisfy the requirement.

### 4. Two decisions you made without AI
- I chose a three-app Django structure (`doctors`, `patients`, and `appointments`) because the assessment stated, *"We're starting small but want to grow."* A modular structure makes the project easier to maintain and extend as it grows.
- I chose not to implement authentication because it was outside the scope of the assessment, allowing me to focus on delivering the required functionality.