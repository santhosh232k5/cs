# Smart Home Service Assistant

A premium Urban Company-style marketplace for home and shop services with auto worker assignment, booking lifecycle tracking, and live notifications.

## What is included

- User + worker authentication with role-specific dashboards
- AI-assisted service classification from natural language descriptions
- Voice capture for issue entry (Web Speech API)
- Smart worker assignment:
  - service match
  - city match
  - nearest worker (if GPS is available)
  - lowest active job load fallback
- Full booking flow:
  - Pending → Worker Assigned → Worker On The Way → Job In Progress → Completed
- Worker actions:
  - Accept / Reject job
  - Update job status
  - Earnings summary
- Notification center:
  - bell icon + unread badge
  - dropdown panel
  - mark all read
  - user and worker event notifications

## Tech Stack

- Frontend: HTML, modern CSS (responsive), vanilla JavaScript
- Backend: Python Flask
- Database: MongoDB (PyMongo)

## Run locally

1. Start MongoDB (`mongodb://localhost:27017/` by default).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start app:
   ```bash
   flask --app app run --debug
   ```

Optional environment variables:

- `MONGO_URI` (default: `mongodb://localhost:27017/`)
- `MONGO_DB` (default: `smart_home_service_assistant`)
- `SECRET_KEY`

## Key Collections

- `users`
- `technicians`
- `bookings`
- `notifications`
