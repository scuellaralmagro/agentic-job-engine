import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { IngestCard } from "./IngestCard";

// NB: the handler deliberately does not call request.formData() — parsing a
// multipart body from a jsdom File never resolves under MSW, which hangs the
// mutation. The Content-Type header proves the body went out as FormData.
test("uploads the file as multipart and handles the merged profile", async () => {
  let contentType: string | null = null;
  server.use(
    http.post("/api/profile/ingest", ({ request }) => {
      contentType = request.headers.get("content-type");
      return HttpResponse.json({
        contact: {
          full_name: null,
          headline: null,
          email: null,
          phone: null,
          location: null,
          links: [],
        },
        skills: [
          { name: "Python", category: null, level: null, source_refs: [1] },
        ],
        experiences: [],
        education: [],
        achievements: [],
        languages: [],
      });
    }),
  );
  renderWithProviders(<IngestCard />);

  await userEvent.upload(
    screen.getByLabelText(/upload/i),
    new File(["dummy"], "cv.pdf", { type: "application/pdf" }),
  );

  // Back to the idle label once the request settles.
  await waitFor(() =>
    expect(screen.getByText(/ingest cv/i)).toBeInTheDocument(),
  );
  // apiFetch must leave FormData alone rather than forcing application/json.
  expect(contentType).toMatch(/^multipart\/form-data/);
});
