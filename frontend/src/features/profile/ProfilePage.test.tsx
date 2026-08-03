import { http, HttpResponse } from "msw";
import { screen } from "@testing-library/react";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import type { ProfileData } from "@/lib/api/types";
import { ProfilePage } from "./ProfilePage";

const profile: ProfileData = {
  contact: {
    full_name: "Sam Doe",
    headline: "Backend Engineer",
    email: "sam@example.com",
    phone: null,
    location: "Madrid",
    links: [],
  },
  skills: [
    { name: "Python", category: "Languages", level: "expert", source_refs: [1] },
    { name: "Docker", category: "Tools", level: null, source_refs: [] },
  ],
  experiences: [
    {
      company: "Acme",
      title: "Engineer",
      description: null,
      start: "2020",
      end: null,
      bullets: ["Built APIs"],
      skills: ["Python"],
      source_refs: [1],
    },
  ],
  education: [],
  achievements: [],
  languages: [{ name: "Spanish", level: "native", source_refs: [] }],
};

test("renders contact, totals, and provenance badges", async () => {
  server.use(
    http.get("/api/profile", () => HttpResponse.json(profile)),
    http.get("/api/source-documents", () => HttpResponse.json([])),
  );
  renderWithProviders(<ProfilePage />);

  expect(await screen.findByText("Sam Doe")).toBeInTheDocument();
  expect(screen.getByText("Python")).toBeInTheDocument();
  expect(screen.getByText(/Acme/)).toBeInTheDocument();
  // Docker has no source_refs → manual provenance
  expect(screen.getAllByText("manual").length).toBeGreaterThan(0);
});
