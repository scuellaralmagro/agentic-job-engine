import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { SearchPage } from "./SearchPage";

function mockBase(runs: unknown[] = []) {
  server.use(
    http.get("/api/runs", () => HttpResponse.json(runs)),
    http.get("/api/searches", () => HttpResponse.json([])),
    http.get("/api/runs/estimate", () =>
      HttpResponse.json({
        max_offers: 150,
        cost_per_offer_usd: 0.011,
        max_cost_usd: 1.65,
      }),
    ),
  );
}

test("the estimate is presented as a ceiling before launching", async () => {
  mockBase();
  renderWithProviders(<SearchPage />);

  await userEvent.type(screen.getByLabelText(/search query/i), "python madrid");
  await userEvent.click(screen.getByRole("button", { name: /^run search$/i }));

  expect(await screen.findByText(/ceiling, not a forecast/i)).toBeInTheDocument();
  expect(screen.getByText("$1.65")).toBeInTheDocument();
});

test("the cap lowers the projected spend", async () => {
  mockBase();
  renderWithProviders(<SearchPage />);

  await userEvent.type(screen.getByLabelText(/search query/i), "python");
  await userEvent.type(screen.getByLabelText(/max offers to score/i), "10");
  await userEvent.click(screen.getByRole("button", { name: /^run search$/i }));

  expect(await screen.findByText("$0.11")).toBeInTheDocument();
});

test("launching creates a run and does not claim it finished", async () => {
  mockBase();
  let posted: unknown = null;
  server.use(
    http.post("/api/runs", async ({ request }) => {
      posted = await request.json();
      return HttpResponse.json({
        id: 9,
        saved_search_id: null,
        kind: "manual",
        term: "python madrid",
        filters: {},
        status: "running",
        offers_found: 0,
        offers_new: 0,
        source_results: [],
        started_at: "2026-08-03T10:00:00",
        finished_at: null,
      });
    }),
  );
  renderWithProviders(<SearchPage />);

  await userEvent.type(screen.getByLabelText(/search query/i), "python madrid");
  await userEvent.click(screen.getByRole("button", { name: /^run search$/i }));
  await userEvent.click(await screen.findByRole("button", { name: /start run/i }));

  await waitFor(() => expect(posted).toMatchObject({ term: "python madrid" }));
});

test("run history shows both kinds with their query", async () => {
  mockBase([
    {
      id: 1,
      saved_search_id: 2,
      kind: "scheduled",
      term: "python",
      filters: {},
      status: "ok",
      offers_found: 12,
      offers_new: 3,
      source_results: [],
      started_at: "2026-08-03T09:00:00",
      finished_at: "2026-08-03T09:01:00",
    },
    {
      id: 2,
      saved_search_id: null,
      kind: "manual",
      term: "golang remote",
      filters: {},
      status: "running",
      offers_found: 0,
      offers_new: 0,
      source_results: [],
      started_at: "2026-08-03T10:00:00",
      finished_at: null,
    },
  ]);
  renderWithProviders(<SearchPage />);

  expect(await screen.findByText("golang remote")).toBeInTheDocument();
  expect(screen.getByText("python")).toBeInTheDocument();
  expect(screen.getAllByRole("link", { name: /view/i })).toHaveLength(2);
});
