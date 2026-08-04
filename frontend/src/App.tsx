import { useEffect, useState } from "react";

import ReviewDetailPage from "./pages/ReviewDetailPage";
import ReviewsPage from "./pages/ReviewsPage";

function getReviewIdFromHash(): string | null {
  const match = window.location.hash.match(/^#review\/(.+)$/);
  return match ? decodeURIComponent(match[1]) : null;
}

function App() {
  const [selectedReviewId, setSelectedReviewId] = useState<string | null>(() =>
    getReviewIdFromHash(),
  );

  useEffect(() => {
    function handleHashChange() {
      setSelectedReviewId(getReviewIdFromHash());
    }

    window.addEventListener("hashchange", handleHashChange);
    return () => window.removeEventListener("hashchange", handleHashChange);
  }, []);

  function selectReview(reviewId: string) {
    window.location.hash = `review/${encodeURIComponent(reviewId)}`;
    setSelectedReviewId(reviewId);
  }

  function clearReview() {
    window.history.pushState("", document.title, window.location.pathname);
    setSelectedReviewId(null);
  }

  if (selectedReviewId) {
    return <ReviewDetailPage reviewId={selectedReviewId} onBack={clearReview} />;
  }

  return <ReviewsPage onSelectReview={selectReview} />;
}

export default App;
