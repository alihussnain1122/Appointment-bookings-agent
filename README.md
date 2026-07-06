# Smile Dental — Voice Appointment System

AI-powered dental clinic booking with voice calls, admin monitoring, MongoDB, and Google Sheets.

## Project structure

| Folder | Purpose |
|---|---|
| `server/` | Booking API (Express + MongoDB + Google Sheets) |
| `ai-agent/` | AI agent (Groq) + voice WebSocket server |
| `frontend/` | Patient call UI + admin dashboard |

## Run everything (3 terminals)

### 1. Booking API
```powershell
cd server
npm install
npm run dev
```
Runs on `http://localhost:5000`

### 2. Voice call server
```powershell
cd ai-agent
pip install -r requirements.txt
python web_server.py
```
Runs on `http://localhost:8000`

### 3. Frontend
```powershell
cd frontend
npm install
npm run dev
```
Open `http://localhost:5173`

## Pages

- **Patient call:** `http://localhost:5173/` — click **Call** to talk with Maya and book an appointment
- **Admin:** `http://localhost:5173/admin` — enter PIN (default `1234`), listen to live transcripts, **End call**

## Environment

Copy examples and fill in secrets:
- `server/.env.example` → `server/.env`
- `ai-agent/.env.example` → `ai-agent/.env`
- `frontend/.env.example` → `frontend/.env`

Set `ADMIN_PIN` in `ai-agent/.env` for admin dashboard access.

## CLI voice agent (optional)

```powershell
cd ai-agent
python voice_agent.py
```
