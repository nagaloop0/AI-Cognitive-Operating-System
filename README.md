# AI Cognitive Operating System

A proactive AI Cognitive Operating System that observes user behavior (app usage, input patterns, time spent) to learn patterns and suggest context-aware workflows.

This project serves as a foundational layer toward behavioral Brain-Computer Interface (BCI) systems.

## Core Principles (Absolute Privacy)
1. **Zero Content Logging:** The system only counts keystrokes and mouse clicks. It *never* logs actual characters typed.
2. **Zero Screen Capture:** The system only asks the OS for the active window's metadata.
3. **Local First:** All behavioral data is stored locally in a PostgreSQL database (`cognitive_os`).

## macOS Permissions Required
To enable global window tracking and privacy-safe input counts on macOS:
1. **Screen Recording:** Required by Quartz to read active window titles. (System Settings -> Privacy & Security -> Screen & System Audio Recording -> Terminal / IDE -> ON).
2. **Accessibility:** Required by `pynput` to listen for global keypress and mouse click counts. (System Settings -> Privacy & Security -> Accessibility -> Terminal / IDE -> ON).
*Note: If you recreate your virtual environment or change Python binaries, macOS security invalidates the executable signature and you must toggle Accessibility off and on again.*

## Activity Tracking & Use Cases
We track keystroke and mouse click **counts** (never content) to unlock key metrics:
* **Presence & Idle Detection:** Differentiates between when an app is open in the background (0 key/mouse inputs) vs when you are actively typing/clicking. If inactive, the session is marked as "Idle" after a timeout.
* **Context Mapping:** Distinguishes passive consumption (reading/watching tutorials: low keystrokes, high mouse activity) from active generation (coding/writing docs: high keystrokes, low mouse activity).

## Tech Stack
* **Backend Tracker:** Python (AppKit, Quartz, pynput)
* **Database:** PostgreSQL (SQLAlchemy ORM)
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