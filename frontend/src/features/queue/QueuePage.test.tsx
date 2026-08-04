import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import type { MatchOut } from "@/lib/api/types";
import { QueuePage } from "./QueuePage";

function makeMatch(overrides: Partial<MatchOut> = {}): MatchOut {
  return {
    id: 1,
    offer_id: 10,
    offer: {
      id: 10,
      title: "Backend Engineer",
      company: "Acme",
      location: "Madrid",
      seniority: "senior",
      // Most real postings never state it; the row must cope with null.
      work_mode: null,
      skills: ["python"],
      description: "desc",
      url: null,
      source: "adzuna",
      posted_at: null,
      created_at: "2026-08-01T00:00:00",
    },
    fitness: 88,
    rubric: {},
    dealbreaker: false,
    dealbreaker_reason: null,
    gaps: [{ requirement: "Kubernetes", severity: "minor" }],
    explanation: null,
    above_threshold: true,
    status: "new",
    scored_by: "rubric",
    similarity: null,
    scored_at: null,
    ...overrides,
  };
}

test("renders matches with fitness and offer info", async () => {
  server.use(http.get("/api/queue", () => HttpResponse.json([makeMatch()])));
  renderWithProviders(<QueuePage />, { route: "/queue", path: "/queue" });

  expect(await screen.findByText("Backend Engineer")).toBeInTheDocument();
  expect(screen.getByTestId("fitness-badge")).toHaveTextContent("88%");
});

test("dismiss removes the row optimistically, before the server responds", async () => {
  let dismissed = false;
  let releaseDismiss: () => void = () => {};
  const dismissPending = new Promise<void>((resolve) => {
    releaseDismiss = resolve;
  });

  server.use(
    // Mirrors the backend: a dismissed match leaves the status=new queue.
    http.get("/api/queue", () =>
      HttpResponse.json(dismissed ? [] : [makeMatch()]),
    ),
    http.post("/api/matches/1/dismiss", async () => {
      await dismissPending;
      dismissed = true;
      return HttpResponse.json(makeMatch({ status: "dismissed" }));
    }),
  );
  renderWithProviders(<QueuePage />, { route: "/queue", path: "/queue" });
  await screen.findByText("Backend Engineer");

  await userEvent.click(screen.getByRole("button", { name: /dismiss/i }));

  // The row is gone while the request is still in flight.
  await waitFor(() =>
    expect(screen.queryByText("Backend Engineer")).not.toBeInTheDocument(),
  );

  releaseDismiss();
  // …and stays gone once the server confirms and the queue refetches.
  await waitFor(() =>
    expect(screen.queryByText("Backend Engineer")).not.toBeInTheDocument(),
  );
});

test("text filter narrows the list client-side", async () => {
  server.use(
    http.get("/api/queue", () =>
      HttpResponse.json([
        makeMatch(),
        makeMatch({
          id: 2,
          offer: { ...makeMatch().offer!, id: 11, title: "Data Scientist" },
        }),
      ]),
    ),
  );
  renderWithProviders(<QueuePage />, { route: "/queue", path: "/queue" });
  await screen.findByText("Data Scientist");

  await userEvent.type(screen.getByPlaceholderText(/search/i), "data");

  expect(screen.queryByText("Backend Engineer")).not.toBeInTheDocument();
  expect(screen.getByText("Data Scientist")).toBeInTheDocument();
});
