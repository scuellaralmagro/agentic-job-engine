import { http, HttpResponse } from "msw";
import { screen, waitFor } from "@testing-library/react";
import { server } from "@/test/server";
import { renderWithProviders } from "@/test/render";
import { Layout } from "./Layout";

test("renders nav links and health indicator", async () => {
  server.use(http.get("/api/health", () => HttpResponse.json({ status: "ok" })));
  renderWithProviders(<Layout />);

  for (const label of [
    "Dashboard",
    "Queue",
    "Library",
    "Profile",
    "Settings",
  ]) {
    expect(
      screen.getByRole("link", { name: new RegExp(label, "i") }),
    ).toBeInTheDocument();
  }
  // The dot starts "down" and flips once the health query resolves.
  await waitFor(() =>
    expect(screen.getByTestId("health-dot")).toHaveAttribute(
      "data-status",
      "ok",
    ),
  );
});
