// Offers & matches
export interface OfferOut {
  id: number;
  title: string;
  company: string | null;
  location: string | null;
  seniority: string | null;
  skills: string[];
  description: string | null;
  url: string | null;
  source: string;
  posted_at: string | null;
  created_at: string;
}

export interface RubricCriterion {
  score: number;
  evidence: string;
}

export interface Gap {
  requirement: string;
  severity: string;
}

export type MatchStatus = "new" | "accepted" | "dismissed";

export interface MatchOut {
  id: number;
  offer_id: number;
  offer: OfferOut | null;
  fitness: number;
  rubric: Record<string, RubricCriterion>;
  gaps: Gap[];
  explanation: string | null;
  above_threshold: boolean;
  status: MatchStatus;
  scored_by: string;
  similarity: number | null;
  scored_at: string | null;
}

// Discovery
export interface RunOut {
  id: number;
  saved_search_id: number | null;
  status: "ok" | "partial" | "failed";
  offers_found: number;
  offers_new: number;
  source_results: unknown[];
  started_at: string;
  finished_at: string | null;
}

export interface SearchOut {
  id: number;
  name: string;
  query: string;
  filters: Record<string, unknown>;
  schedule: string | null;
  created_at: string;
}

// Adaptation
export interface TailoredBullet {
  source_key: string;
  text: string;
}

export interface TailoredExperience {
  source_key: string;
  bullets: TailoredBullet[];
}

export interface TailoredCv {
  language: string;
  headline: string;
  summary: string;
  experiences: TailoredExperience[];
  skill_keys: string[];
  achievement_keys: string[];
  education_keys: string[];
  language_keys: string[];
}

export interface Suggestion {
  kind: string;
  source_key: string;
  before: string | null;
  after: string | null;
  reason: string;
}

export interface ProjectionOut {
  id: number;
  name: string;
  offer_id: number | null;
  match_id: number | null;
  language: string | null;
  content_json: TailoredCv;
  suggestions: Suggestion[];
  created_at: string;
}

export interface DocOut {
  id: number;
  kind: "cv" | "cover_letter";
  offer_id: number | null;
  cv_projection_id: number | null;
  pdf_ref: string;
  created_at: string;
}

export interface CoverLetterContent {
  language: string;
  salutation: string;
  paragraphs: string[];
  closing: string;
}

export interface LetterOut {
  id: number;
  match_id: number | null;
  offer_id: number | null;
  language: string | null;
  content_json: CoverLetterContent;
  created_at: string;
}

// Profile
export interface ContactLink {
  label: string;
  url: string;
}

export interface Contact {
  full_name: string | null;
  headline: string | null;
  email: string | null;
  phone: string | null;
  location: string | null;
  links: ContactLink[];
}

export interface Skill {
  name: string;
  category: string | null;
  level: string | null;
  source_refs: number[];
}

export interface Experience {
  company: string;
  title: string;
  description: string | null;
  start: string | null;
  end: string | null;
  bullets: string[];
  skills: string[];
  source_refs: number[];
}

export interface Education {
  institution: string;
  degree: string | null;
  field: string | null;
  start: string | null;
  end: string | null;
  source_refs: number[];
}

export interface Achievement {
  text: string;
  source_refs: number[];
}

export interface LanguageItem {
  name: string;
  level: string | null;
  source_refs: number[];
}

export interface ProfileData {
  contact: Contact;
  skills: Skill[];
  experiences: Experience[];
  education: Education[];
  achievements: Achievement[];
  languages: LanguageItem[];
}

export interface SourceDocumentOut {
  id: number;
  kind: string;
  status: string;
  file_ref: string;
  created_at: string;
}
