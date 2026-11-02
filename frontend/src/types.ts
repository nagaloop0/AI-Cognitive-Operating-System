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


// ---- Phase 2: AI summary, categories and assistant messages ----

export interface TimeSplit {
  app_name: string;
  minutes: number;
}

export interface DailySummary {
  day: string;
  headline: string;
  focus_areas: string[];
  insight: string;
  suggestion: string;
  time_split: TimeSplit[];
  active_minutes: number;
  category_minutes: Record<string, number>;
  source: 'llm' | 'fallback';
  model: string | null;
  attempts: number;
  is_partial: boolean;
  generated_at: string;
  notice: string | null;
}

export interface AssistantMessage {
  id: number;
  created_at: string;
  kind: 'welcome_back' | 'end_of_day' | 'nudge' | 'unread';
  title: string;
  body: string;
  is_read: boolean;
}

export interface AskSource {
  day: string;
  app_name: string;
  window_title: string;
  seconds: number;
}

export interface AskAnswer {
  question: string;
  answer: string;
  days: string[];
  sources: AskSource[];
}
