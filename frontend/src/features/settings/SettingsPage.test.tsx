import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { SettingsPage } from "./SettingsPage";

function mockBase() {
  server.use(
    http.get("/api/searches", () =>
      HttpResponse.json([
        {
          id: 1,
          name: "Python Madrid",
          query: "python backend",
          filters: { location: "Madrid" },
          schedule: "0 8 * * *",
          created_at: "2026-08-01T00:00:00",
        },
      ]),
    ),
  );
}

test("lists saved searches with schedule", async () => {
  mockBase();
  renderWithProviders(<SettingsPage />);

  expect(await screen.findByText("Python Madrid")).toBeInTheDocument();
  expect(screen.getByText("0 8 * * *")).toBeInTheDocument();
});

test("creates a search via the dialog", async () => {
  mockBase();
  let posted: unknown = null;
  server.use(
    http.post("/api/searches", async ({ request }) => {
      posted = await request.json();
      return HttpResponse.json({
        id: 2,
        name: "Data",
        query: "data engineer",
        filters: {},
        schedule: null,
        created_at: "2026-08-03T00:00:00",
      });
    }),
  );
  renderWithProviders(<SettingsPage />);
  await screen.findByText("Python Madrid");

  await userEvent.click(screen.getByRole("button", { name: /new search/i }));
  await userEvent.type(await screen.findByLabelText(/^name$/i), "Data");
  await userEvent.type(screen.getByLabelText(/^query$/i), "data engineer");
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  await waitFor(() => expect(posted).not.toBeNull());
  expect(posted).toMatchObject({ name: "Data", query: "data engineer" });
});

test("imports an offer from pasted text", async () => {
  mockBase();
  let imported: unknown = null;
  server.use(
    http.post("/api/offers/import", async ({ request }) => {
      imported = await request.json();
      return HttpResponse.json({ id: 99, title: "Imported" });
    }),
  );
  renderWithProviders(<SettingsPage />);
  await screen.findByText("Python Madrid");

  await userEvent.type(
    screen.getByLabelText(/paste a job description or url/i),
    "Great Python job at Acme",
  );
  await userEvent.click(screen.getByRole("button", { name: /import offer/i }));

  await waitFor(() =>
    expect(imported).toMatchObject({ text: "Great Python job at Acme" }),
  );
});
