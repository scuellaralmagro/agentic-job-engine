import { fitnessLevel } from "./fitness";

test.each([
  [92, "high"],
  [75, "high"],
  [74.9, "medium"],
  [50, "medium"],
  [49.9, "low"],
  [0, "low"],
])("fitnessLevel(%f) → %s", (fitness, expected) => {
  expect(fitnessLevel(fitness)).toBe(expected);
});
