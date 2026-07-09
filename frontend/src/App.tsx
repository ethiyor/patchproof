import { apiClient } from "./api/client";

const apiBaseUrl = apiClient.defaults.baseURL ?? "http://localhost:8000";

function App() {
  return (
    <main className="min-h-screen bg-surface text-ink">
      <section className="mx-auto flex min-h-screen w-full max-w-6xl flex-col gap-8 px-6 py-8">
        <header className="flex flex-col gap-3 border-b border-line pb-6 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
              PatchProof
            </p>
            <h1 className="mt-2 text-3xl font-semibold tracking-normal text-ink">
              Review Dashboard
            </h1>
          </div>
          <div className="rounded-md border border-line bg-white px-3 py-2 text-sm text-slate-600 shadow-sm">
            API: {apiBaseUrl}
          </div>
        </header>

        <div className="grid gap-4 md:grid-cols-3">
          <section className="rounded-md border border-line bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">Reviews</p>
            <p className="mt-3 text-3xl font-semibold">Ready</p>
          </section>
          <section className="rounded-md border border-line bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">Backend</p>
            <p className="mt-3 text-3xl font-semibold text-ready">Connected</p>
          </section>
          <section className="rounded-md border border-line bg-white p-5 shadow-sm">
            <p className="text-sm font-medium text-slate-500">Mode</p>
            <p className="mt-3 text-3xl font-semibold">Read-only</p>
          </section>
        </div>

        <section className="rounded-md border border-line bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold">Dashboard scaffold is running</h2>
          <p className="mt-3 max-w-3xl text-sm leading-6 text-slate-600">
            The React app is ready for the review list page. The API client is
            configured through VITE_API_URL and defaults to the local FastAPI
            backend.
          </p>
        </section>
      </section>
    </main>
  );
}

export default App;
