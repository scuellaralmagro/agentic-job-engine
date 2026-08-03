import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import type { MatchOut, ProjectionOut } from "@/lib/api/types";
import { AdaptActions } from "./AdaptActions";

const accepted = { id: 5, offer_id: 10, status: "accepted" } as MatchOut;

const projection: ProjectionOut = {
  id: 3,
  name: "CV — Backend Engineer",
  offer_id: 10,
  match_id: 5,
  language: "en",
  content_json: {
    language: "en",
    headline: "",
    summary: "",
    experiences: [],
    skill_keys: [],
    achievement_keys: [],
    education_keys: [],
    language_keys: [],
  },
  suggestions: [
    {
      kind: "emphasize",
      source_key: "exp:1",
      before: null,
      after: null,
      reason: "Match",
    },
  ],
  created_at: "2026-08-03T00:00:00",
};

test("adapt is disabled until accepted", async () => {
  server.use(
    http.get("/api/projections", () => HttpResponse.json([])),
    http.get("/api/cover-letters", () => HttpResponse.json([])),
  );
  renderWithProviders(
    <AdaptActions match={{ ...accepted, status: "new" } as MatchOut} />,
  );
  expect(screen.getByRole("button", { name: /adapt cv/i })).toBeDisabled();
});

test("adapt creates a projection and links to its editor", async () => {
  let adapted = false;
  server.use(
    http.get("/api/projections", () =>
      HttpResponse.json(adapted ? [projection] : []),
    ),
    http.get("/api/cover-letters", () => HttpResponse.json([])),
    http.post("/api/matches/5/adapt", () => {
      adapted = true;
      return HttpResponse.json(projection);
    }),
  );
  renderWithProviders(<AdaptActions match={accepted} />);

  await userEvent.click(screen.getByRole("button", { name: /adapt cv/i }));

  await waitFor(() =>
    expect(
      screen.getByRole("link", { name: /CV — Backend Engineer/i }),
    ).toHaveAttribute("href", "/library/projections/3"),
  );
  expect(screen.getByText(/1 suggestion/i)).toBeInTheDocument();
});
