import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { DashboardPage } from "./DashboardPage";

function mockAll({ runs = [] as unknown[] } = {}) {
  server.use(
    http.get("/api/queue", ({ request }) => {
      const status = new URL(request.url).searchParams.get("status");
      return HttpResponse.json(
        status === "new"
          ? [
              {
                id: 1,
                offer_id: 10,
                offer: {
                  id: 10,
                  title: "Backend Engineer",
                  company: "Acme",
                  location: null,
                  seniority: null,
                  skills: [],
                  description: null,
                  url: null,
                  source: "test",
                  posted_at: null,
                  created_at: new Date().toISOString(),
                },
                fitness: 91,
                rubric: {},
                gaps: [],
                explanation: null,
                above_threshold: true,
                status: "new",
                scored_by: "rubric",
                similarity: null,
                scored_at: null,
              },
            ]
          : [],
      );
    }),
    http.get("/api/offers", () => HttpResponse.json([])),
    http.get("/api/runs", () => HttpResponse.json(runs)),
    http.get("/api/searches", () => HttpResponse.json([])),
    http.get("/api/generated-docs", () => HttpResponse.json([])),
  );
}

test("shows stat cards and top matches", async () => {
  mockAll();
  renderWithProviders(<DashboardPage />);

  expect(await screen.findByText("Backend Engineer")).toBeInTheDocument();
  expect(screen.getByText(/pending review/i)).toBeInTheDocument();
  expect(screen.getByTestId("fitness-badge")).toHaveTextContent("91%");
});

test("shows running chip for an active run", async () => {
  mockAll({
    runs: [
      {
        id: 7,
        saved_search_id: 1,
        status: "ok",
        offers_found: 0,
        offers_new: 0,
        source_results: [],
        started_at: new Date().toISOString(),
        finished_at: null,
      },
    ],
  });
  renderWithProviders(<DashboardPage />);
  expect(await screen.findByText(/running/i)).toBeInTheDocument();
});
