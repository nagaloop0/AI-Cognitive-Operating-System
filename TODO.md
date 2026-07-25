# AI Cognitive OS - Project TODO & Ideas List

This list contains high-level ideas, future expansions, and configuration ideas to implement as the system matures.

## Future Platforms & Clients
- [ ] **Cross-Platform Support:** Expand OS trackers to include Windows (`win32gui`) and Linux (`xlib`).
- [ ] **Chrome Extension:** Build a browser extension to track specific URLs and in-tab active time (going beyond simple window titles).
- [ ] **Mobile Applications:**
  - Build Android app (APK) for mobile usage tracking.
  - Port to Apple App Store (iOS Screen Time / focus tracking).
- [ ] **Desktop Wrapper:** Pack the python driver and Vue 3 dashboard into a unified application (e.g., using Electron or Tauri).
- [ ] **Unified Process Manager:** Create a single master launcher script to run `driver.py` (tracker daemon) and `server.py` (FastAPI backend) in parallel without needing two separate terminal windows.

## Core Enhancements & Preferences
- [ ] **Settings Dashboard Panel:** Allow users to set focus preferences, tracking schedules, and notification settings directly in the Vue UI.
- [ ] **Custom Alarms / Proactive Alerts:** Enable the backend to trigger actions or alerts (alarms) based on the user's custom preferences.
- [ ] **Interactive Alerts:** Refine how suggestions are shown:
  - macOS Slide-in notifications (Standard)
  - Dashboard proactive widget (Standard)
  - Voice Command ("Jarvis Mode" for Phase 2)

## Database & Data Structures
- [ ] **XML Data Structure Feasibility:** Investigate using XML formatting for exporting data relationships, configurations, or patterns.
- [ ] **Pre-define Database Schemas:** Design Phase 2 tables (Habits, AI predictions, and User Preferences) during Phase 1 to avoid complex migrations later.
