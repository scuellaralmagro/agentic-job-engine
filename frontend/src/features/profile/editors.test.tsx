import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { Experience, Skill } from "@/lib/api/types";
import { ExperiencesEditor, SkillsEditor } from "./editors";

const skills: Skill[] = [
  { name: "Python", category: "Languages", level: null, source_refs: [1] },
];

test("removes a skill chip", async () => {
  const onChange = vi.fn();
  render(<SkillsEditor skills={skills} onChange={onChange} />);

  await userEvent.click(screen.getByRole("button", { name: /remove python/i }));

  expect(onChange).toHaveBeenCalledWith([]);
});

test("adds a skill with manual provenance", async () => {
  const onChange = vi.fn();
  render(<SkillsEditor skills={skills} onChange={onChange} />);

  await userEvent.click(screen.getByRole("button", { name: /add skill/i }));
  await userEvent.type(screen.getByLabelText(/name/i), "FastAPI");
  await userEvent.click(screen.getByRole("button", { name: /^add$/i }));

  expect(onChange).toHaveBeenCalledWith([
    ...skills,
    { name: "FastAPI", category: null, level: null, source_refs: [] },
  ]);
});

test("edits an experience bullet via dialog", async () => {
  const experiences: Experience[] = [
    {
      company: "Acme",
      title: "Engineer",
      description: null,
      start: "2020",
      end: null,
      bullets: ["Built APIs"],
      skills: [],
      source_refs: [],
    },
  ];
  const onChange = vi.fn();
  render(<ExperiencesEditor experiences={experiences} onChange={onChange} />);

  await userEvent.click(screen.getByRole("button", { name: /edit engineer/i }));
  const bullets = await screen.findByLabelText(/bullets/i);
  await userEvent.clear(bullets);
  await userEvent.type(bullets, "Shipped v2 API");
  await userEvent.click(screen.getByRole("button", { name: /^save$/i }));

  expect(onChange).toHaveBeenCalledWith([
    { ...experiences[0], bullets: ["Shipped v2 API"] },
  ]);
});
