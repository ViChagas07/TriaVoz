export type User = {
  id: string;
  email: string;
  full_name: string;
  role: "admin" | "attendant" | string;
  is_active: boolean;
  created_at?: string | null;
};

export type Me = { user: User; clinic_id: string; role: string };

export type RequestStatus = "pending" | "in_progress" | "done" | "cancelled" | "spam";
export type RequestType = "appointment" | "exam_pickup" | "message" | "callback" | "other";
export type Priority = "urgent" | "normal" | "low";

export type ServiceRequest = {
  id: string;
  clinic_id: string;
  type: RequestType | string;
  title: string;
  description: string | null;
  status: RequestStatus | string;
  priority: Priority | string;
  patient_name: string | null;
  patient_phone: string | null;
  requested_date: string | null;
  due_date: string | null;
  assigned_to: string | null;
  assigned_to_name: string | null;
  call_id: string | null;
  suspicion_flags: string[];
  needs_review: boolean;
  created_at: string;
  updated_at: string;
};

export type RequestEvent = {
  id: string;
  event_type: string;
  note: string | null;
  user_id: string | null;
  user_name: string | null;
  created_at: string;
};

export type RequestDetail = ServiceRequest & { timeline: RequestEvent[] };

export type RequestList = { items: ServiceRequest[]; next_cursor: string | null };

export type Call = {
  id: string;
  channel: string;
  caller_number: string | null;
  started_at: string;
  ended_at: string | null;
  status: string;
  end_reason: string | null;
  duration_seconds: number | null;
  summary: string | null;
  abuse_score: number;
  suspicion_flags: string[];
  needs_review: boolean;
  handoff_requested: boolean;
  handoff_completed: boolean;
  cost_cents: number;
};

export type CallDetail = Call & {
  room_name: string | null;
  usage: Record<string, unknown>;
  latency_ms: Record<string, unknown>;
};

export type CallList = { items: Call[]; next_cursor: string | null };

export type CallTurn = {
  id: string;
  seq: number;
  speaker: string;
  content: string;
  tool_name: string | null;
  tool_payload: Record<string, unknown> | null;
  started_at: string;
  stt_confidence: number | null;
};

export type CallEvent = {
  id: string;
  event_type: string;
  payload: Record<string, unknown>;
  created_at: string;
};

export type Appointment = {
  id: string;
  clinic_id: string;
  call_id: string | null;
  starts_at: string;
  ends_at: string;
  status: string;
  customer_name: string;
  customer_phone: string;
  service_id: string;
  service_name: string;
  professional_id: string;
  professional_name: string;
  created_via: string;
};

export type Dashboard = {
  pending_requests: number;
  calls_today: number;
  handoffs_today: number;
  handoff_rate: number;
  cost_today_cents: number;
  avg_duration_seconds: number;
  cost_per_call_cents: number;
  cost_per_minute_cents: number;
  tool_errors_today: number;
  slot_taken_today: number;
  slot_taken_rate: number;
  gatekeeper_blocks_today: number;
  latency_p50_ms: Record<string, number>;
  latency_p95_ms: Record<string, number>;
};

export type BusinessHours = {
  days: number[];
  start: string;
  end: string;
};

export type ClinicSettings = {
  name: string;
  slug: string;
  timezone: string;
  business_hours: BusinessHours | null;
  max_call_seconds: number;
  max_concurrent_calls: number;
  daily_minute_budget: number;
  daily_cost_budget_cents: number;
  kill_switch: boolean;
  hidden_caller_policy: "allow" | "reject";
};

export type Service = {
  id: string;
  name: string;
  duration_min: number;
  price_cents: number;
  is_active: boolean;
};

export type Professional = {
  id: string;
  name: string;
  specialty: string | null;
  is_active: boolean;
  service_ids: string[];
};

export type BlockedNumber = {
  id: string;
  e164: string;
  reason: string | null;
  source: string;
  created_at: string;
  expires_at: string | null;
};

export type TeamUser = User;

export type AgentConfig = {
  schema_version: number;
  clinic_name: string;
  greeting: string;
  tone: string;
  emergency_message: string;
};

export type ConfigVersion = {
  id: string;
  version: number;
  status: string;
  config: AgentConfig;
  created_by: string | null;
  created_at: string;
  published_at: string | null;
};

export type AgentConfigState = {
  published: ConfigVersion | null;
  latest_draft: ConfigVersion | null;
};

export type VoiceSession = {
  call_id: string | null;
  room_name: string | null;
  token: string | null;
  url: string | null;
  mode: "session" | "fallback" | "emergency";
  reason: string | null;
  message: string | null;
  handoff: boolean;
  max_call_seconds: number | null;
  timezone: string | null;
};
