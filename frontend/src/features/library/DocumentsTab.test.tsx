import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { DocumentsTab } from "./DocumentsTab";

test("lists docs with kind, offer title and download link", async () => {
  server.use(
    http.get("/api/generated-docs", () =>
      HttpResponse.json([
        {
          id: 9,
          kind: "cv",
          offer_id: 10,
          cv_projection_id: 3,
          pdf_ref: "data/docs/cv-3.pdf",
          created_at: "2026-08-03T10:00:00",
        },
      ]),
    ),
    http.get("/api/offers", () =>
      HttpResponse.json([
        {
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
          created_at: "2026-08-01T00:00:00",
        },
      ]),
    ),
    http.get("/api/cover-letters", () => HttpResponse.json([])),
  );
  renderWithProviders(<DocumentsTab />);

  expect(await screen.findByText("Backend Engineer")).toBeInTheDocument();
  expect(screen.getByText("cv")).toBeInTheDocument();
  expect(screen.getByRole("link", { name: /download/i })).toHaveAttribute(
    "href",
    "/api/docs/9/download",
  );
});
