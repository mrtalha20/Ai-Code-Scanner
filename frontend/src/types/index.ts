export type ScanStatus = "pending" | "running" | "done" | "failed";

export interface Finding {
  id: string;
  owasp_category: string;
  title: string;
  description: string;
  severity: number;
  severity_justification: string;
  line_start: number | null;
  line_end: number | null;
  vulnerable_code: string;
  fixed_code: string;
  fix_explanation: string;
  diff_summary: string;
  function_name: string | null;
}

export interface Scan {
  id: string;
  status: ScanStatus;
  language: string;
  repo_url: string | null;
  pr_number: number | null;
  created_at: string;
  completed_at: string | null;
  findings: Finding[];
  error_message: string | null;
}

export interface WsMessage {
  event: "progress" | "finding" | "done" | "error" | "ping";
  stage?: string;
  finding?: Finding;
  message?: string;
  progress_pct?: number;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
}

export interface User {
  id: string;
  email: string;
  role: string;
  plan: string;
  created_at: string;
}
