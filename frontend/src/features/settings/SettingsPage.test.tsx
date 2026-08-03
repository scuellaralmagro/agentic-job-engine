import { screen } from "@testing-library/react";
import { renderWithProviders } from "@/test/render";
import { SettingsPage } from "./SettingsPage";

test("settings keeps only configuration", () => {
  renderWithProviders(<SettingsPage />);

  expect(screen.getByText("System")).toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: /rebuild embeddings/i }),
  ).toBeInTheDocument();
  // these moved to the Search tab, which owns discovery now
  expect(screen.queryByText("Saved searches")).not.toBeInTheDocument();
  expect(
    screen.queryByLabelText(/paste a job description/i),
  ).not.toBeInTheDocument();
});
