export type FitnessLevel = "high" | "medium" | "low";

export function fitnessLevel(fitness: number): FitnessLevel {
  if (fitness >= 75) return "high";
  if (fitness >= 50) return "medium";
  return "low";
}
