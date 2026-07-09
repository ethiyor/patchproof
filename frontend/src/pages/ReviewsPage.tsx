import { useEffect, useState } from "react";

import { apiClient, fetchReviews, type ReviewListItem } from "../api/client";
import ReviewCard from "../components/ReviewCard";

type LoadState = "loading" | "ready" | "empty" | "error";

const apiBaseUrl = apiClient.defaults.baseURL ?? "http://localhost:8000";

function ReviewsPage() {
  const [reviews, setReviews] = useState<ReviewListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [state, setState] = useState<LoadState>("loading");

  useEffect(() => {
    let isMounted = true;

    async function loadReviews() {
      setState("loading");
      try {
        const data = await fetchReviews();
        if (!isMounted) {
          return;
        }
        setReviews(data.reviews);
        setTotal(data.total);
        setState(data.reviews.length > 0 ? "ready" : "empty");
      } catch {
        if (isMounted) {
          setState("error");
        }
      }
    }

    void loadReviews();

    return () => {
      isMounted = false;
    };
  }, []);

  return (
    <main className="min-h-screen bg-surface text-ink">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-6 px-6 py-8">
        <header className="flex flex-col gap-3 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
              PatchProof
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">
              Reviews
            </h1>
          </div>
          <div className="rounded-md border border-line bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
            API: {apiBaseUrl}
          </div>
        </header>

        <section className="grid gap-4 sm:grid-cols-3">
          <div className="rounded-md border border-line bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">Saved reviews</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{total}</p>
          </div>
          <div className="rounded-md border border-line bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">Visible</p>
            <p className="mt-2 text-3xl font-semibold text-ink">{reviews.length}</p>
          </div>
          <div className="rounded-md border border-line bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">View</p>
            <p className="mt-3 text-base font-semibold text-slate-700">
              Review history
            </p>
          </div>
        </section>

        {state === "loading" && (
          <section className="flex min-h-72 items-center justify-center rounded-md border border-line bg-white shadow-sm">
            <div className="flex items-center gap-3 text-sm font-medium text-slate-600">
              <span className="h-5 w-5 animate-spin rounded-full border-2 border-slate-300 border-t-ink" />
              Loading reviews
            </div>
          </section>
        )}

        {state === "error" && (
          <section className="rounded-md border border-red-200 bg-red-50 p-6 text-sm font-medium text-red-700">
            Failed to load reviews.
          </section>
        )}

        {state === "empty" && (
          <section className="rounded-md border border-line bg-white p-8 text-center text-sm font-medium text-slate-600 shadow-sm">
            No reviews yet. Run patchproof review to get started.
          </section>
        )}

        {state === "ready" && (
          <section className="grid gap-4 lg:grid-cols-2">
            {reviews.map((review) => (
              <ReviewCard key={review.review_id} review={review} />
            ))}
          </section>
        )}
      </section>
    </main>
  );
}

export default ReviewsPage;
