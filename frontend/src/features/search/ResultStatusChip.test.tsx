import { render, screen } from "@testing-library/react";
import type { ResultMatch } from "@/lib/api/types";
import { ResultStatusChip, ReviewChip } from "./ResultStatusChip";

test("the scoring state is visually live", () => {
  render(<ResultStatusChip status="scoring" error={null} />);
  const chip = screen.getByTestId("result-status");
  expect(chip).toHaveAttribute("data-status", "scoring");
  expect(chip.className).toContain("animate-pulse");
});

test("prefiltered explains that no llm call happened", () => {
  render(<ResultStatusChip status="prefiltered" error={null} />);
  expect(screen.getByTestId("result-status").getAttribute("title")).toContain(
    "no LLM call",
  );
});

test("a failure surfaces its error", () => {
  render(<ResultStatusChip status="failed" error="llm down" />);
  expect(screen.getByTestId("result-status")).toHaveAttribute("title", "llm down");
});

test("review status is rendered separately from pipeline status", () => {
  const match: ResultMatch = {
    id: 1,
    fitness: 80,
    status: "dismissed",
    above_threshold: true,
  };
  render(
    <>
      <ResultStatusChip status="scored" error={null} />
      <ReviewChip match={match} />
    </>,
  );
  // "rejected by the prefilter" and "rejected by you" must stay distinguishable
  expect(screen.getByTestId("result-status")).toHaveTextContent(/scored/i);
  expect(screen.getByTestId("review-status")).toHaveTextContent(/dismissed/i);
});

test("an unreviewed match reads as queued only when above threshold", () => {
  render(
    <ReviewChip match={{ id: 1, fitness: 40, status: "new", above_threshold: false }} />,
  );
  expect(screen.getByTestId("review-status")).toHaveTextContent("—");
});

test("an above-threshold unreviewed match reads as queued", () => {
  render(
    <ReviewChip match={{ id: 1, fitness: 80, status: "new", above_threshold: true }} />,
  );
  expect(screen.getByTestId("review-status")).toHaveTextContent("queued");
});
