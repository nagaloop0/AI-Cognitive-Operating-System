# AI Cognitive Operating System

A proactive AI Cognitive Operating System that observes user behavior (app usage, input patterns, time spent) to learn patterns and suggest context-aware workflows.

This project serves as a foundational layer toward behavioral Brain-Computer Interface (BCI) systems.

## Core Principles (Absolute Privacy)
1. **Zero Content Logging:** The system only counts keystrokes and mouse clicks. It *never* logs actual characters typed.
2. **Zero Screen Capture:** The system only asks the OS for the active window's metadata.
3. **Local First:** All behavioral data is stored locally in an SQLite database at `~/.cognitive_os/activity.db`.

## Tech Stack
* **Backend Tracker:** Python (AppKit, pynput)
* **Database:** SQLite (SQLAlchemy ORM)
* **API:** FastAPI
* **Dashboard:** Vue 3

## Phase 1 (Current)
Data Collection & Base System. The goal is to track active applications and input counts, build patterns, and display them in a dashboard using simple rule-based suggestions.

## Local Setup (Development)
```bash
# 1. Create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Verify Database
python test_db.py
```