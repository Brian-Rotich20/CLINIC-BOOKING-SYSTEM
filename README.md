# Clinic Booking API

A REST API for a small clinic (5 doctors) to manage online appointment
booking — patients can view a doctor's free slots, book, cancel, or
reschedule. Built for the Savannah Informatics Backend Developer take-home
assessment.

- **Live URL:** https://clinic-booking-system-8k20.onrender.com/
- **Repo:** [ADD YOUR GITHUB REPO URL HERE]
- **API docs (Swagger UI):** https://clinic-booking-system-8k20.onrender.com/api/schema/swagger-ui/
- **Stack:** Python · Django · Django REST Framework · PostgreSQL · Render · GitHub Actions

> Note: the root URL (`/`) returns a 404 by design — there's no homepage.
> Use `/admin/` to browse data, or the Swagger UI link above to explore and
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

---

## API Endpoints

Full interactive documentation (with "try it out") is available at:
**https://clinic-booking-system-8k20.onrender.com/api/schema/swagger-ui/**

### `POST /appointments`
Books a slot.
```json
// Request
{
  "doctor_id": 1,
  "patient_id": 1,
  "start_time": "2026-08-10T10:00:00Z"
}
```
Returns `201` with the created appointment, or `400` (invalid slot / outside
working hours / in the past / within 1hr lead time) or `409` (slot already
taken).

### `GET /doctors/{id}/availability?date=YYYY-MM-DD`
Returns available 30-minute slots for that doctor on that date.
```json
// Response
[
  {"start_time": "2026-08-10T09:00:00Z"},
  {"start_time": "2026-08-10T09:30:00Z"}
]
```

### `PATCH /appointments/{id}/cancel`
```json
// Request
{"reason": "patient requested cancellation"}
```
Returns `200` with the updated appointment, or `400` if already cancelled or
reason is missing, or `404` if not found.

### `PATCH /appointments/{id}/reschedule`
```json
// Request
{"start_time": "2026-08-10T11:00:00Z"}
```
Returns `200` with the updated appointment. New slot is validated exactly as
a fresh booking would be. Returns `400` if the appointment is already
cancelled, or `409` if the new slot is taken.

### Bonus: `GET /patients/{id}/appointments`
Returns the patient's upcoming, non-cancelled appointments sorted by date.

---

## Running Locally

```bash
git clone [YOUR_REPO_URL]
cd clinic-booking
python3 -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env          # fill in your DB credentials
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
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

---

## AI Reflection

> Draft — personalize this before submitting. This should reflect your
> actual experience, in your own words; the assessment explicitly grades
> honesty here over the "right" answer.

**1. What did you use AI for across the four sections?**
- Section 1: talking through the system design — identifying entities,
  weighing single-app vs. multi-app structure, deciding what belongs in a
  `services.py` layer vs. views/serializers.
- Section 2: drafting models, serializers, views, the custom exception
  handler, and the booking/cancel/reschedule business logic in `services.py`,
  plus the test suite.
- Section 3: drafting the GitHub Actions workflow, `build.sh`, Render-specific
  settings changes (WhiteNoise, `ALLOWED_HOSTS`, `DEBUG`), and adding
  `@extend_schema` annotations for Swagger UI.
- Section 4: this reflection itself, as a starting draft.

**2. One example where an AI suggestion improved your work.**
[Fill with a specific example — e.g. the two-layer double-booking guard
(pre-validation + DB-level `UniqueConstraint` inside `transaction.atomic()`)
was suggested when discussing how to prevent race conditions on concurrent
booking requests. Prompt: "what happens if two patients book the same slot
at the same time?" What made it a genuine improvement rather than just
AI-generated code: explain briefly, in your own words.]

**3. One example where AI output was wrong or incomplete, and how you caught it.**
[Fill with something real — e.g. an early `views.py` draft wasn't actually
saved to disk before running `createsuperuser`, causing an `ImportError`
that looked like a code problem but was a workflow mistake on your end — you
caught it by reading the traceback file path carefully rather than assuming
the code itself was broken. If there's a clearer example from your own
process, use that instead — this one is more "your own catch" than "AI being
wrong."]

**4. Two decisions you made without AI. Why did you trust your own judgment there?**
- Choosing the three-app structure over a single app, after AI laid out the
  trade-off — the call itself (and the reasoning about the clinic's stated
  growth intent) was yours.
- Deciding auth was out of scope for this assessment — a scope judgment
  based on reading the brief, not a technical question AI was better
  positioned to answer.