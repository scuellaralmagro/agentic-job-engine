import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { SearchDialog } from "./SearchDialog";
import type { SearchOut } from "@/lib/api/types";

function mockEstimate() {
  server.use(
    http.get("/api/runs/estimate", () =>
      HttpResponse.json({
        max_offers: 150,
        cost_per_offer_usd: 0.011,
        max_cost_usd: 1.65,
      }),
    ),
  );
}

const existing: SearchOut = {
  id: 1,
  name: "AI Engineer",
  query: "ai engineer",
  filters: {},
  schedule: "0 8 * * *",
  max_offers: 25,
  created_at: "2026-08-01T00:00:00",
};

test("a new search is pre-filled with the default cap", async () => {
  mockEstimate();
  renderWithProviders(
    <SearchDialog search={null} open onOpenChange={() => {}} />,
  );

  expect(await screen.findByLabelText(/max offers per run/i)).toHaveValue("25");
});

test("the cap is priced per run, and per month when scheduled", async () => {
  mockEstimate();
  renderWithProviders(
    <SearchDialog search={existing} open onOpenChange={() => {}} />,
  );

  // 25 x $0.011 = $0.275, which toFixed(2) renders as 0.27: the float is
  // 0.27499... Same arithmetic as RunSearchCard, so the two stay consistent.
  expect(await screen.findByText(/\$0\.27 per run/)).toBeInTheDocument();
  expect(screen.getByText(/\$8\.25\/month if it runs daily/)).toBeInTheDocument();
});

test("clearing the cap warns that the search is uncapped", async () => {
  mockEstimate();
  renderWithProviders(
    <SearchDialog search={existing} open onOpenChange={() => {}} />,
  );

  await userEvent.clear(await screen.findByLabelText(/max offers per run/i));

  expect(await screen.findByText(/uncapped/i)).toBeInTheDocument();
  expect(screen.getByText(/up to 150 offers/)).toBeInTheDocument();
});

test("saving sends the cap, and sends null when it is cleared", async () => {
  mockEstimate();
  let posted: Record<string, unknown> | null = null;
  server.use(
    http.put("/api/searches/1", async ({ request }) => {
      posted = (await request.json()) as Record<string, unknown>;
      return HttpResponse.json({ ...existing, max_offers: null });
    }),
  );
  renderWithProviders(
    <SearchDialog search={existing} open onOpenChange={() => {}} />,
  );

  await userEvent.clear(await screen.findByLabelText(/max offers per run/i));
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  await screen.findByText(/uncapped/i);
  expect(posted).not.toBeNull();
  expect(posted!.max_offers).toBeNull();
});
