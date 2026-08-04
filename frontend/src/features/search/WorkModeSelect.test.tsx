import { useState } from "react";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";
import { WorkModeSelect } from "./WorkModeSelect";
import type { WorkMode } from "@/lib/api/types";

function Harness() {
  const [value, setValue] = useState<WorkMode[]>([]);
  return (
    <>
      <WorkModeSelect value={value} onChange={setValue} />
      <output data-testid="value">{value.join(",") || "(none)"}</output>
    </>
  );
}

describe("WorkModeSelect", () => {
  it("selects nothing by default, which means no filtering", () => {
    render(<Harness />);

    expect(screen.getByTestId("value")).toHaveTextContent("(none)");
    expect(screen.getByRole("button", { name: "Remote" })).toHaveAttribute(
      "aria-pressed",
      "false",
    );
  });

  it("toggles modes on and off independently", async () => {
    const user = userEvent.setup();
    render(<Harness />);

    await user.click(screen.getByRole("button", { name: "Remote" }));
    await user.click(screen.getByRole("button", { name: "Hybrid" }));
    expect(screen.getByTestId("value")).toHaveTextContent("remote,hybrid");

    await user.click(screen.getByRole("button", { name: "Remote" }));
    expect(screen.getByTestId("value")).toHaveTextContent("hybrid");
    expect(screen.getByRole("button", { name: "Hybrid" })).toHaveAttribute(
      "aria-pressed",
      "true",
    );
  });

});
