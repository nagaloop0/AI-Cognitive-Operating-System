---
name: cognitive-os
description: >-
  Technical architecture, operational runbooks, database schemas, and API documentation
  for the AI Cognitive Operating System project (explore_p).
---

# AI Cognitive Operating System - Technical Knowledge Base

A proactive AI Cognitive Operating System observing user behavior (active applications, input intensity, dwell time) to predict context-aware workflows and serve as a behavioral Brain-Computer Interface (BCI) foundational layer.

---

## 1. Core Architecture

The system operates across 4 coordinated tiers:

```
[macOS Quartz / AppKit]  +  [pynput Listener]
         │                          │
         └───────────┬──────────────┘
                     ▼
             backend/driver.py  (Polling 2s, Idle Timeout 20s)
                     │
                     ▼
           PostgreSQL (cognitive_os)
                     │
                     ▼
          backend/main.py  (FastAPI REST Server, Port 8000)
                     │
                     ▼
         frontend/  (Vue 3 + TypeScript Dashboard - Hour 5)
```

---

## 2. Privacy Guarantees (Non-Negotiable)

1. **Zero Keystroke / Content Logging**: Keypresses and mouse clicks are tracked as atomic integer increments (`+1`). Typed characters, strings, passwords, and screen coordinates are never recorded or stored.
2. **Zero Screen Capture**: Never takes screenshots or frame grabs. Only reads active window metadata (Application Name, Window Title) from the OS window manager.
3. **Local-First Database**: All activity is stored in a local PostgreSQL database (`cognitive_os`). No telemetry is sent to any external cloud.
4. **User Privacy Controls**: Instant pause/resume toggle and permanent history deletion via API endpoints.

---

## 3. Database Schema (PostgreSQL via SQLAlchemy)

Defined in `backend/models.py`:

* **`app_activity`**:
  * `id` (Integer, Primary Key)
  * `start_time`, `end_time` (DateTime with UTC timezone)
  * `app_name` (String, indexed)
  * `window_title` (String)
  * `keystroke_count`, `mouse_click_count` (Integer)
  * `duration_seconds` (Integer)
* **`user_preference`**:
  * `key` (String, unique, indexed - e.g. `"is_tracking_paused"`)
  * `value` (String)
  * `updated_at` (DateTime with timezone)
* **`habit_pattern`** (Pre-provisioned for Hour 6):
  * `trigger_sequence`, `predicted_action`, `occurrence_count`, `confidence`, `last_triggered`
* **`ai_prediction`** (Pre-provisioned for Phase 2):
  * `timestamp`, `trigger_sequence`, `suggested_action`, `status` (`accepted`/`ignored`/`dismissed`)

---

## 4. macOS Security & Permissions Setup

Because macOS Quartz and pynput tap into global system events, the running terminal/IDE requires:
1. **Screen & System Audio Recording**: `System Settings -> Privacy & Security -> Screen Recording -> [Terminal / IDE / Python] -> ON` (Required for window titles).
2. **Accessibility**: `System Settings -> Privacy & Security -> Accessibility -> [Terminal / IDE / Python] -> ON` (Required for global key/mouse listeners).

*Note: If the Python binary or virtual environment is recreated, macOS invalidates the previous permission signature; toggle the permissions OFF and ON again.*

---

## 5. Daily Execution Runbook

When the virtual environment is activated (`source venv/bin/activate` or `(venv)` showing):

### Step A: Sanity Checks (5 seconds)
```bash
# Verify database connection
python test/test_db.py

# Verify macOS window tracking permissions
python test/test_tracker.py
```

### Step B: Start Backend REST API
```bash
python server.py
# Server runs at: http://localhost:8000
# Interactive Swagger docs: http://localhost:8000/docs
```

### Step C: Start Background Tracking Daemon
```bash
python -m backend.driver
# Starts 2-second polling loop and idle detection (20s)
```

---

## 6. REST API Endpoints Reference

Base URL: `http://127.0.0.1:8000`

| Method | Endpoint | Description | Sample Output |
| :--- | :--- | :--- | :--- |
| `GET` | `/` | Health check | `{"message": "AI Cognitive OS API is online and running."}` |
| `GET` | `/api/stats/summary` | Overall totals | `{"total_duration_seconds": 120, "total_keystrokes": 45, ...}` |
| `GET` | `/api/stats/apps` | Aggregated app stats | `[{"app_name": "Google Chrome", "total_duration_seconds": 90, ...}]` |
| `GET` | `/api/stats/timeline?limit=20` | Chronological session logs | `[{"id": 1, "app_name": "Code", "duration_seconds": 40, ...}]` |
| `GET` | `/api/control/status` | Current tracking state | `{"is_tracking_paused": false}` |
| `POST` | `/api/control/toggle` | Remote pause/resume switch | `{"is_tracking_paused": true}` |
| `POST` | `/api/control/clear-history` | Delete all activity rows | `{"message": "Successfully deleted 12 activity records."}` |

---

## 7. Project Roadmap

* **Phase 1: Telemetry & Foundation**
  * `[x]` Hour 1: Core Data Layer (SQLAlchemy + PostgreSQL)
  * `[x]` Hour 2: OS Application Tracking (AppKit + Quartz)
  * `[x]` Hour 3: Privacy Input Counter & Driver Loop (pynput + Idle Timeout)
  * `[x]` Hour 4: FastAPI REST API & Remote Controls
  * `[ ]` Hour 5: Vue 3 + TypeScript Frontend Dashboard
  * `[ ]` Hour 6: Statistical Pattern Recognition (Markov Chains & macOS Notifications)
* **Phase 2: Local AI & Intention Modeling**
  * Local LLM (Ollama)
  * Semantic Task Clustering (Vector Embeddings)
  * Fuzzy Sequence Prediction
  * Half-Life Habit Decay Weighting
  * Proactive Voice / Jarvis Mode
