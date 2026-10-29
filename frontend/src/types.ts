// TypeScript DTOs matching backend/schemas.py

export interface OverallSummary {
  total_duration_seconds: number;
  total_keystrokes: number;
  total_clicks: number;
  total_sessions: number;
}

export interface AppSummary {
  app_name: string;
  total_duration_seconds: number;
  total_keystrokes: number;
  total_clicks: number;
  session_count: number;
}

export interface TimelineItem {
  id: number;
  app_name: string;
  window_title: string;
  start_time: string;
  end_time: string | null;
  duration_seconds: number;
  keystroke_count: number;
  mouse_click_count: number;
}

export interface PreferenceStatus {
  is_tracking_paused: boolean;
}

export interface MessageResponse {
  message: string;
}

export interface HabitPatternItem {
  id: number;
  trigger_sequence: string;
  predicted_action: string;
  occurrence_count: number;
  confidence: number;
  last_triggered: string | null;
}

export interface PredictionItem {
  id: number;
  timestamp: string;
  trigger_sequence: string;
  suggested_action: string;
  status: 'suggested' | 'accepted' | 'ignored' | string;
}

export interface DashboardData {
  summary: OverallSummary;
  apps: AppSummary[];
  timeline: TimelineItem[];
  preference: PreferenceStatus;
  patterns?: HabitPatternItem[];
  recent_predictions?: PredictionItem[];
}

