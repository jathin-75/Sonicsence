     # SonicSense AI

**Real-time environmental sound detection and classification system.**

SonicSense AI is a full-stack platform that identifies environmental sounds — such as dog barks, glass breaking, sirens, speech, and more — from uploaded audio files, using a real pretrained deep learning model (YAMNet). It includes secure user authentication, role-based access (User/Admin), and a live monitoring dashboard.

---

## Features

- 🔐 Secure user registration & login (JWT-based sessions, hashed passwords)
- 🎯 Real AI sound classification using Google's YAMNet model (521 sound classes)
- 🏷️ Specific, human-readable labels (e.g. "Dog Bark" instead of raw model output)
- 🎧 Upload audio files and instantly hear + see the detected sound
- 📊 Live dashboard: confidence gauge, detection feed, sound-class grid, history timeline
- 🚨 Critical sound alert mode (gunshots, fire alarms, glass breaking, sirens)
- 🕓 Per-user prediction history stored in a database
- 👤 Role-based access control (User / Admin)

---

## Tech Stack

**Backend:** Python, FastAPI, SQLAlchemy, SQLite, Passlib (bcrypt), python-jose (JWT), Uvicorn

**AI/ML:** TensorFlow, TensorFlow Hub (YAMNet), Librosa

**Frontend:** HTML5, CSS3, Vanilla JavaScript, Web Audio API, WebSocket API

---

## Project Structure
sonicsense/
├── backend/
│   ├── main.py            # FastAPI app & API routes
│   ├── models.py          # Database models (User, Prediction)
│   ├── auth.py             # Password hashing & JWT logic
│   ├── database.py        # SQLite/SQLAlchemy setup
│   ├── classifier.py      # YAMNet-based sound classification
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── style.css
│   └── app.js
└── README.md

---

## Setup Instructions

### 1. Backend

```bash
cd backend
python -m venv venv

# Activate the virtual environment
# Windows:
venv\Scripts\Activate.ps1
# Mac/Linux:
source venv/bin/activate

pip install -r requirements.txt
pip install tensorflow tensorflow-hub librosa soundfile numpy

uvicorn main:app --reload
```

The backend will start at `http://127.0.0.1:8000`. The first run downloads the YAMNet model (~15MB) automatically. API documentation is available at `http://127.0.0.1:8000/docs`.

### 2. Frontend

No build step required. Simply open `frontend/index.html` directly in your browser (double-click the file, or use a tool like VS Code's Live Server extension).

> Make sure the backend is running first — the frontend expects it at `http://127.0.0.1:8000`.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/auth/register` | Create a new account, returns JWT token |
| POST | `/auth/login` | Log in, returns JWT token |
| GET | `/auth/me` | Get current user's profile |
| PUT | `/auth/me` | Update current user's profile |
| POST | `/upload` | Upload an audio file for classification |
| GET | `/history` | Get the user's prediction history |
| GET | `/health` | Server health check |
| WS | `/ws/live` | WebSocket for live detection stream |
| GET | `/admin/users` | List all users (admin only) |
| GET | `/admin/stats` | System-wide statistics (admin only) |

---

## Security Note

⚠️ Before deploying this publicly or sharing this repository widely:
- Change `SECRET_KEY` in `backend/auth.py` to a long, random, private value
- Change `ADMIN_SIGNUP_CODE` in `backend/main.py` to a private value not committed to version control (consider moving both into environment variables)

---

## Screenshots

*(Add screenshots of the login screen, dashboard, and detection results here.)*

---

## Roadmap

- [ ] Real-time live microphone classification (currently upload-only for real AI inference)
- [ ] Docker containerization for deployment
- [ ] PostgreSQL for production-scale usage
- [ ] Dedicated Admin panel UI
- [ ] Edge deployment (Raspberry Pi, ESP32)

---

## License

Internal project — not yet licensed for public distribution.