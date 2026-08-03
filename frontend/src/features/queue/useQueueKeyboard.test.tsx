import { fireEvent, render, screen } from "@testing-library/react";
import type { MatchOut } from "@/lib/api/types";
import { useQueueKeyboard } from "./useQueueKeyboard";

const rows = [{ id: 1 }, { id: 2 }] as MatchOut[];

function Harness({ onDismiss }: { onDismiss: (m: MatchOut) => void }) {
  const selectedId = useQueueKeyboard(rows, {
    onAccept: () => {},
    onDismiss,
  });
  return <p data-testid="sel">{String(selectedId)}</p>;
}

test("j/k move selection and d dismisses the selected row", () => {
  const onDismiss = vi.fn();
  render(<Harness onDismiss={onDismiss} />);

  fireEvent.keyDown(window, { key: "j" });
  expect(screen.getByTestId("sel")).toHaveTextContent("1");
  fireEvent.keyDown(window, { key: "j" });
  expect(screen.getByTestId("sel")).toHaveTextContent("2");
  fireEvent.keyDown(window, { key: "k" });
  expect(screen.getByTestId("sel")).toHaveTextContent("1");

  fireEvent.keyDown(window, { key: "d" });
  expect(onDismiss).toHaveBeenCalledWith(rows[0]);
});

test("ignores keys typed into inputs", () => {
  const onDismiss = vi.fn();
  render(
    <>
      <input aria-label="filter" />
      <Harness onDismiss={onDismiss} />
    </>,
  );
  const input = screen.getByLabelText("filter");
  input.focus();
  fireEvent.keyDown(input, { key: "d" });
  expect(onDismiss).not.toHaveBeenCalled();
});
