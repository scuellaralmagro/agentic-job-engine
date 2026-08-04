import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import type { MatchOut } from "@/lib/api/types";
import { MatchDetailPage } from "./MatchDetailPage";

const match: MatchOut = {
  id: 5,
  offer_id: 10,
  offer: {
    id: 10,
    title: "Backend Engineer",
    company: "Acme",
    location: "Madrid",
    seniority: "senior",
    work_mode: "hybrid",
    skills: ["python", "fastapi"],
    description: "Build APIs all day.",
    url: "https://example.com/job",
    source: "adzuna",
    posted_at: null,
    created_at: "2026-08-01T00:00:00",
  },
  fitness: 82,
  rubric: {
    skills: { score: 90, evidence: "Python, FastAPI" },
    seniority: { score: 70, evidence: "5 years" },
  },
  dealbreaker: false,
  dealbreaker_reason: null,
  gaps: [{ requirement: "Kubernetes", severity: "minor" }],
  explanation: "Strong overlap on core stack.",
  above_threshold: true,
  status: "new",
  scored_by: "rubric",
  similarity: null,
  scored_at: null,
};

test("renders offer, rubric bars, gaps and explanation", async () => {
  server.use(
    http.get("/api/matches/5", () => HttpResponse.json(match)),
    http.get("/api/projections", () => HttpResponse.json([])),
    http.get("/api/cover-letters", () => HttpResponse.json([])),
  );
  renderWithProviders(<MatchDetailPage />, {
    route: "/matches/5",
    path: "/matches/:id",
  });

  expect(await screen.findByText("Backend Engineer")).toBeInTheDocument();
  expect(screen.getByText("Build APIs all day.")).toBeInTheDocument();
  expect(screen.getByText(/skills/i)).toBeInTheDocument();
  expect(screen.getByText(/kubernetes/i)).toBeInTheDocument();
  expect(screen.getByText("Strong overlap on core stack.")).toBeInTheDocument();
  expect(screen.getByTestId("fitness-dial")).toHaveTextContent("82%");
  expect(screen.getByText(/Acme · Madrid · senior · Hybrid/)).toBeInTheDocument();
});
