import { render, screen } from "@testing-library/react";
import type { MatchOut } from "@/lib/api/types";
import { FitnessPanel } from "./FitnessPanel";

const base: MatchOut = {
  id: 5,
  offer_id: 10,
  offer: null,
  fitness: 82,
  rubric: {
    skills: { score: 93, evidence: "JavaScript, TypeScript" },
    seniority: { score: 62, evidence: "3 years" },
  },
  dealbreaker: false,
  dealbreaker_reason: null,
  gaps: [],
  explanation: null,
  above_threshold: true,
  status: "new",
  scored_by: "rubric",
  similarity: null,
  scored_at: null,
};

test("renders a bar per scored dimension", () => {
  render(<FitnessPanel match={base} />);

  expect(screen.getByText("skills")).toBeInTheDocument();
  expect(screen.getByText("seniority")).toBeInTheDocument();
  expect(screen.getByTestId("fitness-dial")).toHaveTextContent("82%");
});

test("survives a rubric carrying non-dimension entries", () => {
  // real stored rubrics also hold `dealbreaker` and a null `dealbreaker_reason`;
  // reading .score off those is what crashed the whole route
  const messy = {
    ...base,
    // deliberately the raw stored shape, which the type does not describe
    rubric: {
      ...base.rubric,
      dealbreaker: false,
      dealbreaker_reason: null,
    } as unknown as MatchOut["rubric"],
  };

  render(<FitnessPanel match={messy} />);

  expect(screen.getByText("skills")).toBeInTheDocument();
  expect(screen.queryByText("dealbreaker_reason")).not.toBeInTheDocument();
});

test("a dealbreaker is shown rather than silently dropped", () => {
  render(
    <FitnessPanel
      match={{
        ...base,
        dealbreaker: true,
        dealbreaker_reason: "Requires a work permit the candidate lacks",
      }}
    />,
  );

  expect(screen.getByText(/dealbreaker/i)).toBeInTheDocument();
  expect(screen.getByText(/work permit/i)).toBeInTheDocument();
});
