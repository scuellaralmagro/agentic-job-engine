import { render, screen } from "@testing-library/react";
import App from "./App";

test("renders app heading", () => {
  render(<App />);
  expect(
    screen.getByRole("heading", { name: /agentic job engine/i })
  ).toBeInTheDocument();
});
