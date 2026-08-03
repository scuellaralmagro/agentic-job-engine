import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import type { ProjectionOut } from "@/lib/api/types";
import { LibraryPage } from "./LibraryPage";

const projection: ProjectionOut = {
  id: 3,
  name: "CV — Backend Engineer",
  offer_id: 10,
  match_id: 5,
  language: "en",
  content_json: {
    language: "en",
    headline: "Backend Engineer",
    summary: "",
    experiences: [],
    skill_keys: [],
    achievement_keys: [],
    education_keys: [],
    language_keys: [],
  },
  suggestions: [],
  created_at: "2026-08-03T00:00:00",
};

test("lists projection cards with editor link", async () => {
  server.use(
    http.get("/api/projections", () => HttpResponse.json([projection])),
    http.get("/api/generated-docs", () => HttpResponse.json([])),
    http.get("/api/offers", () => HttpResponse.json([])),
    http.get("/api/cover-letters", () => HttpResponse.json([])),
  );
  renderWithProviders(<LibraryPage />);

  expect(await screen.findByText("CV — Backend Engineer")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /edit/i })).toHaveAttribute(
    "href",
    "/library/projections/3",
  );
});

test("delete asks for confirmation then calls the API", async () => {
  let deleted = false;
  server.use(
    http.get("/api/projections", () =>
      HttpResponse.json(deleted ? [] : [projection]),
    ),
    http.get("/api/generated-docs", () => HttpResponse.json([])),
    http.get("/api/offers", () => HttpResponse.json([])),
    http.get("/api/cover-letters", () => HttpResponse.json([])),
    http.delete("/api/projections/3", () => {
      deleted = true;
      return new HttpResponse(null, { status: 204 });
    }),
  );
  renderWithProviders(<LibraryPage />);
  await screen.findByText("CV — Backend Engineer");

  await userEvent.click(screen.getByRole("button", { name: /delete/i }));
  await userEvent.click(await screen.findByRole("button", { name: /confirm/i }));

  await waitFor(() =>
    expect(screen.queryByText("CV — Backend Engineer")).not.toBeInTheDocument(),
  );
});
