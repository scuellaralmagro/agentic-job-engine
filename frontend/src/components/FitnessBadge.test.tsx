import { render, screen } from "@testing-library/react";
import { FitnessBadge } from "./FitnessBadge";

test("shows rounded percentage", () => {
  render(<FitnessBadge fitness={87.4} />);
  expect(screen.getByTestId("fitness-badge")).toHaveTextContent("87%");
});

test("colors by level", () => {
  render(<FitnessBadge fitness={30} />);
  expect(screen.getByTestId("fitness-badge").className).toContain("text-danger");
});
