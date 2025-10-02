// API Types
export interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status?: string;
}

// Authentication Types
export interface User {
  id: string;
  role: 'ADMIN' | 'TRADER';
  apiKey: string;
}

// KPI Types
export interface Provenance {
  doc: string;
  page: number;
  table: string;
  row: number;
  col: number;
}

export interface KpiData {
  ticker: string;
  period: string;
  metric: string;
  current_value: number;
  unit: string;
  yoy_change?: number;
  qoq_change?: number;
  consensus?: number;
  surprise?: number;
  provenance: Provenance;
  confidence: number;
}

// Signal Types
export interface Citation {
  doc: string;
  page: number;
  table: string;
  text: string;
}

export interface Signal {
  ticker: string;
  period: string;
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number;
  reasons: string[];
  citations: Citation[];
  blocked_reason?: string;
  generated_at: string;
}

// Signal Strength Chart Types
export interface SignalDataPoint {
  timestamp: string;
  ticker: string;
  signalStrength: number; // -100 to +100
  action: 'BUY' | 'SELL' | 'HOLD';
  confidence: number; // 0-1
  reasons: string[];
  citations: Citation[];
  generated_at: string;
}

// Subscription Types
export interface Subscription {
  id: number;
  user_id: string;
  ticker: string;
  channels: string[];
  created_at: string;
}

export interface SubscriptionCreate {
  ticker: string;
  channels: ('ws' | 'slack' | 'email')[];
}

// Search Types
export interface SearchResult {
  doc: string;
  page: number;
  text: string;
  score: number;
  ticker?: string;
}

export interface SearchResponse {
  query: string;
  results: SearchResult[];
  total_results: number;
}

// Notification Types
export interface NotificationEvent {
  event: string;
  data: any;
  timestamp: string;
}

export interface DocEvent {
  event: 'NEW_DOC_INGESTED';
  doc_id: string;
  ticker: string;
  period?: string;
  doc_type: string;
  received_at: string;
}

export interface SignalEvent {
  event: 'NEW_SIGNAL_READY';
  ticker: string;
  action: string;
  confidence: number;
  citations: Citation[];
}

export interface ComplianceEvent {
  event: 'COMPLIANCE_ALERT';
  ticker: string;
  message: string;
  effective_date: string;
  citations: Citation[];
  exposure_guidance?: string;
}

// Upload Types
export interface UploadResponse {
  doc_id: string;
  ticker: string;
  period?: string;
  doc_type: string;
  status: string;
  message: string;
}

// Dashboard Types
export interface DashboardStats {
  totalDocuments: number;
  totalSignals: number;
  activeSubscriptions: number;
  processingQueue: number;
  systemUptime: string;
}

export interface TickerSummary {
  ticker: string;
  last_updated: string;
  signal?: Signal;
  kpis: { [key: string]: KpiData };
  compliance: any;
  available_periods: string[];
}

// Chart Types
export interface ChartData {
  name: string;
  value: number;
  change?: number;
}

export interface TimeSeriesData {
  date: string;
  value: number;
  ticker: string;
}

// Error Types
export interface ApiError {
  detail: string;
  status_code?: number;
  error_code?: string;
}
