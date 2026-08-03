import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { RunDetailPage } from "./RunDetailPage";

const offer = {
  id: 10,
  title: "Backend Engineer",
  company: "Acme",
  location: "Madrid",
  seniority: "senior",
  skills: ["python"],
  description: "desc",
  url: null,
  source: "tecnoempleo",
  posted_at: null,
  created_at: "2026-08-01T00:00:00",
};

function mockRun(status: string, results: unknown[]) {
  server.use(
    http.get("/api/runs/5", () =>
      HttpResponse.json({
        id: 5,
        saved_search_id: null,
        kind: "manual",
        term: "python madrid",
        filters: {},
        status,
        offers_found: results.length,
        offers_new: 1,
        source_results: [{ source: "tecnoempleo", count: 1, error: null }],
        started_at: "2026-08-03T10:00:00",
        finished_at: status === "running" ? null : "2026-08-03T10:01:00",
      }),
    ),
    http.get("/api/runs/5/results", () => HttpResponse.json(results)),
  );
}

const render5 = () =>
  renderWithProviders(<RunDetailPage />, {
    route: "/search/runs/5",
    path: "/search/runs/:id",
  });

test("shows the query and each result's status", async () => {
  mockRun("ok", [
    {
      id: 1,
      offer_id: 10,
      offer,
      is_new: true,
      status: "scored",
      error: null,
      created_at: "2026-08-03T10:00:30",
      match: { id: 3, fitness: 82, status: "new", above_threshold: true },
    },
  ]);
  render5();

  expect(await screen.findByText("python madrid")).toBeInTheDocument();
  expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
  expect(screen.getByTestId("result-status")).toHaveAttribute(
    "data-status",
    "scored",
  );
  expect(screen.getByTestId("review-status")).toHaveTextContent("queued");
  expect(screen.getByTestId("fitness-badge")).toHaveTextContent("82%");
});

test("a prefiltered result is distinguishable from a dismissed one", async () => {
  mockRun("ok", [
    {
      id: 1,
      offer_id: 10,
      offer,
      is_new: true,
      status: "prefiltered",
      error: null,
      created_at: "2026-08-03T10:00:30",
      match: { id: 3, fitness: 12, status: "new", above_threshold: false },
    },
  ]);
  render5();

  expect(await screen.findByTestId("result-status")).toHaveAttribute(
    "data-status",
    "prefiltered",
  );
  expect(screen.getByTestId("review-status")).toHaveTextContent("—");
});

test("the new-only filter hides re-finds", async () => {
  mockRun("ok", [
    {
      id: 1,
      offer_id: 10,
      offer,
      is_new: true,
      status: "scored",
      error: null,
      created_at: "2026-08-03T10:00:30",
      match: null,
    },
    {
      id: 2,
      offer_id: 11,
      offer: { ...offer, id: 11, title: "Data Engineer" },
      is_new: false,
      status: "scored",
      error: null,
      created_at: "2026-08-03T10:00:31",
      match: null,
    },
  ]);
  render5();
  await screen.findByText("Data Engineer");

  await userEvent.click(screen.getByRole("checkbox", { name: /new only/i }));

  expect(screen.queryByText("Data Engineer")).not.toBeInTheDocument();
  expect(screen.getByText("Backend Engineer")).toBeInTheDocument();
});

test("a failing source is surfaced rather than reported as zero", async () => {
  server.use(
    http.get("/api/runs/5", () =>
      HttpResponse.json({
        id: 5,
        saved_search_id: null,
        kind: "manual",
        term: "python",
        filters: {},
        status: "partial",
        offers_found: 0,
        offers_new: 0,
        source_results: [
          { source: "adzuna", count: 0, error: "401 unauthorized" },
        ],
        started_at: "2026-08-03T10:00:00",
        finished_at: "2026-08-03T10:01:00",
      }),
    ),
    http.get("/api/runs/5/results", () => HttpResponse.json([])),
  );
  render5();

  const chip = await screen.findByTitle("401 unauthorized");
  expect(chip).toHaveTextContent(/adzuna/);
});
