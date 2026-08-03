import { http, HttpResponse } from "msw";
import { server } from "@/test/server";
import { apiFetch, ApiError } from "./client";

test("returns parsed JSON on success", async () => {
  server.use(
    http.get("/api/health", () => HttpResponse.json({ status: "ok" })),
  );
  await expect(apiFetch<{ status: string }>("/health")).resolves.toEqual({
    status: "ok",
  });
});

test("throws ApiError with backend detail on failure", async () => {
  server.use(
    http.post("/api/matches/1/adapt", () =>
      HttpResponse.json({ detail: "match not found" }, { status: 404 }),
    ),
  );
  const err = await apiFetch("/matches/1/adapt", { method: "POST" }).catch(
    (e: unknown) => e,
  );
  expect(err).toBeInstanceOf(ApiError);
  expect((err as ApiError).status).toBe(404);
  expect((err as ApiError).detail).toBe("match not found");
});
