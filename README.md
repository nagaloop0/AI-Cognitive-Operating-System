# AI Cognitive Operating System

A proactive AI Cognitive Operating System that observes user behavior (app usage, input patterns, time spent) to learn patterns and suggest context-aware workflows.

This project serves as a foundational layer toward behavioral Brain-Computer Interface (BCI) systems.

## Core Principles & Security Architecture (Absolute Privacy)
1. **Zero Content & Keystroke Logging:** The system only records raw event counts (`+1` integer increments). Typed characters, passwords, credit cards, chat messages, and mouse screen coordinates are **never captured, inspected, or stored**.
2. **Zero Screen Capture:** The system never captures pixels, frames, or screenshots. It only queries the operating system window manager for active application names and window title text.
3. **100% Local-First (Zero Cloud):** All telemetry is stored locally on your machine in PostgreSQL (`127.0.0.1`). No data, telemetry, or analytics ever leave your device or touch the internet.
4. **User Privacy Controls & GDPR Right-to-Erasure:** A remote pause/resume toggle stops the tracking daemon immediately, and a single-click "Wipe History" permanently deletes all stored activity records from the database.
5. **No Authentication Required:** Because the system runs strictly on your private local loopback, there are no user accounts, passwords, or cloud tokens to compromise.

## Architecture: DTO Contracts (Pydantic ↔ TypeScript)
The backend and frontend communicate using strict, mirrored Data Transfer Objects (DTOs):
* **Backend (Python / Pydantic):** `backend/schemas.py` defines runtime-validated schemas (`OverallSummary`, `AppSummary`, `TimelineItem`).
* **Frontend (TypeScript):** `frontend/src/types.ts` mirrors those exact schemas as TypeScript interfaces.
This ensures zero runtime data mismatches or `undefined` property crashes between Python and Vue.

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
Data Collection, REST API & Base System. Tracks active applications, presence, and input activity counts into PostgreSQL, serving analytics via FastAPI to a Vue 3 dashboard with rule-based workflow suggestions.

## Phase 2 (Planned - Intelligence & Local AI)
Intention Modeling & Local AI Engine.
* **Local LLM Integration (Ollama):** Analyze user activity patterns locally without sending data to the cloud.
* **Semantic Clustering (Vector Embeddings):** Group window titles into high-level tasks (e.g. `explore_p` and `AI-OS` -> "Cognitive OS Development").
* **Fuzzy Sequence Prediction:** Predict user workflow intentions semantically across arbitrary application sets.
* **Habit Decay Weighting:** Apply exponential decay functions to prioritize recent 7-day work habits over older activity.
* **Voice Command ("Jarvis Mode"):** Optional local Speech-to-Text and Text-to-Speech interface for natural language activity summaries.

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