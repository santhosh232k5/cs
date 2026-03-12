# Smart Home Service Assistant

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
3. Run app:
   ```bash
   flask --app app run --debug
   ```

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

