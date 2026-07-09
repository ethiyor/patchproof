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

export async function fetchReviews(): Promise<ReviewListResponse> {
  const response = await apiClient.get<ReviewListResponse>("/reviews");
  return response.data;
}
