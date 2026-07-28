import axios from "axios";

export const apiClient = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? "http://localhost:8000",
  headers: {
    "Content-Type": "application/json",
  },
});

export type RiskLevel = "low" | "medium" | "high" | "critical" | string;

export type ReviewListItem = {
  review_id: string;
  repo_name: string;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  merge_recommendation: string | null;
  created_at: string;
};

export type ReviewListResponse = {
  total: number;
  reviews: ReviewListItem[];
};

export type ReviewListParams = {
  page?: number;
  limit?: number;
  risk_level?: string;
};

export type ReviewFinding = {
  category: string | null;
  severity: string | null;
  title: string;
  description: string | null;
  file_path: string | null;
  line_start: number | null;
  line_end: number | null;
  evidence: string | null;
  suggestion: string | null;
};

export type RequirementCheck = {
  requirement_text: string;
  status: string | null;
  evidence: string | null;
  reason: string | null;
};

export type ChangedFile = {
  file_path: string;
  status: string | null;
  language: string | null;
  additions: number;
  deletions: number;
  risk_flags: string[] | null;
};

export type ReviewDetailResponse = {
  review_id: string;
  created_at: string;
  task_text: string | null;
  risk_score: number | null;
  risk_level: RiskLevel | null;
  merge_recommendation: string | null;
  report_markdown: string | null;
  findings: ReviewFinding[];
  requirement_checks: RequirementCheck[];
  changed_files: ChangedFile[];
};

export async function fetchReviews(
  params: ReviewListParams = {},
): Promise<ReviewListResponse> {
  const response = await apiClient.get<ReviewListResponse>("/reviews", { params });
  return response.data;
}

export async function fetchReview(reviewId: string): Promise<ReviewDetailResponse> {
  const response = await apiClient.get<ReviewDetailResponse>(`/reviews/${reviewId}`);
  return response.data;
}
