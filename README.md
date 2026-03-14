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
A full-stack web app that helps users find nearby technicians for common home/shop issues.

## Features

- User and technician registration/login
- AI-assisted issue classification from natural-language text
- Voice-based issue input using browser SpeechRecognition API
- Service request creation with location and optional GPS
- Automatic technician assignment by service + city match
- Request status tracking for users
- Technician dashboard to update request status

## Tech Stack

- Frontend: HTML, CSS, Vanilla JavaScript
- Backend: Python Flask
- Database: MongoDB (via PyMongo)

## Setup

1. Start MongoDB locally (default: `mongodb://localhost:27017/`).
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Start app:
3. Run app:
   ```bash
   flask --app app run --debug
   ```

Optional environment variables:
Optional env vars:

- `MONGO_URI` (default: `mongodb://localhost:27017/`)
- `MONGO_DB` (default: `smart_home_service_assistant`)
- `SECRET_KEY`

## NLP Logic

The chatbot uses keyword-based intent classification in `classify_issue()` and maps user messages into service categories:

- Electrical repair
- Plumbing
- Carpentry
- Painting
- Masonry
- Cleaning
- Appliance repair

