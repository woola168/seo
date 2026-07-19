import type {
  GeoQueryDraftResource,
  GeoQueryGenerationRunResource,
} from "../types";

export function latestGeoQueryRun<T extends { createdAt: string }>(
  runs: readonly T[],
): T | null {
  return [...runs].sort((left, right) =>
    right.createdAt.localeCompare(left.createdAt),
  )[0] ?? null;
}

export function restoredDraftIds(
  generationRun: Pick<GeoQueryGenerationRunResource, "drafts">,
): string[] {
  return generationRun.drafts
    .filter(isRestorableDraft)
    .map((draft) => draft.id);
}

export function runsStartedAtOrAfter<T extends { createdAt: string }>(
  runs: readonly T[],
  startedAt: string,
): T[] {
  if (!startedAt) return [...runs];
  return runs.filter((run) => run.createdAt >= startedAt);
}

export function generationRunsForResearch(
  runs: readonly GeoQueryGenerationRunResource[],
  researchContext: string,
): GeoQueryGenerationRunResource[] {
  if (!researchContext) return [...runs];
  return runs.filter(
    (run) => run.requestPayload.researchContext === researchContext,
  );
}

function isRestorableDraft(draft: GeoQueryDraftResource): boolean {
  return draft.selectionStatus === "shortlisted" && !draft.acceptedQueryId;
}
