import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import type { ProjectionOut } from "@/lib/api/types";
import { ProjectionEditorPage } from "./ProjectionEditorPage";

const projection: ProjectionOut = {
  id: 3,
  name: "CV — Backend Engineer",
  offer_id: 10,
  match_id: 5,
  language: "en",
  content_json: {
    language: "en",
    headline: "Backend Engineer",
    summary: "Seasoned Python developer.",
    experiences: [
      {
        source_key: "exp:acme",
        bullets: [{ source_key: "exp:acme:0", text: "Built APIs" }],
      },
    ],
    skill_keys: ["skill:python"],
    achievement_keys: [],
    education_keys: [],
    language_keys: [],
  },
  suggestions: [
    {
      kind: "rewrite",
      source_key: "exp:acme:0",
      before: "Built APIs",
      after: "Designed and shipped FastAPI services",
      reason: "Mirror the offer's wording",
    },
  ],
  created_at: "2026-08-03T00:00:00",
};

function mock() {
  server.use(
    http.get("/api/projections/3", () => HttpResponse.json(projection)),
  );
}

test("renders editable fields and suggestions", async () => {
  mock();
  renderWithProviders(<ProjectionEditorPage />, {
    route: "/library/projections/3",
    path: "/library/projections/:id",
  });

  expect(
    await screen.findByDisplayValue("Backend Engineer"),
  ).toBeInTheDocument();
  expect(screen.getByDisplayValue("Built APIs")).toBeInTheDocument();
  expect(screen.getByText(/mirror the offer's wording/i)).toBeInTheDocument();
});

test("save PATCHes edited content", async () => {
  mock();
  let patched: unknown = null;
  server.use(
    http.patch("/api/projections/3", async ({ request }) => {
      patched = await request.json();
      return HttpResponse.json(projection);
    }),
  );
  renderWithProviders(<ProjectionEditorPage />, {
    route: "/library/projections/3",
    path: "/library/projections/:id",
  });
  const summary = await screen.findByDisplayValue("Seasoned Python developer.");

  await userEvent.clear(summary);
  await userEvent.type(summary, "Backend specialist.");
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  await waitFor(() => expect(patched).not.toBeNull());
  expect(
    (patched as { content_json: { summary: string } }).content_json.summary,
  ).toBe("Backend specialist.");
});
