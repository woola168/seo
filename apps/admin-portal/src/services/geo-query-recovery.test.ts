import { describe, expect, it } from "vitest";

import type {
  GeoQueryDraftResource,
  GeoQueryGenerationRunResource,
} from "../types";
import {
  generationRunsForResearch,
  latestGeoQueryRun,
  restoredDraftIds,
  runsStartedAtOrAfter,
} from "./geo-query-recovery";

describe("GEO Query Research recovery", () => {
  it("selects the latest run even when the API list is unordered", () => {
    const run = latestGeoQueryRun([
      { id: "older", createdAt: "2026-07-19T01:00:00Z" },
      { id: "newest", createdAt: "2026-07-19T03:00:00Z" },
      { id: "middle", createdAt: "2026-07-19T02:00:00Z" },
    ]);

    expect(run?.id).toBe("newest");
  });

  it("restores only shortlisted drafts that have not been accepted", () => {
    expect(restoredDraftIds({
      drafts: [
        draft("shortlisted", "shortlisted", null),
        draft("rejected", "rejected", null),
        draft("accepted", "accepted", "query-1"),
        draft("pending", null, null),
      ],
    })).toEqual(["shortlisted"]);
  });

  it("excludes runs created before the current operation", () => {
    expect(runsStartedAtOrAfter([
      { id: "old", createdAt: "2026-07-19T01:00:00Z" },
      { id: "current", createdAt: "2026-07-19T02:00:00Z" },
    ], "2026-07-19T02:00:00Z").map((run) => run.id)).toEqual(["current"]);
  });

  it("matches Generation runs to the recovered Research context", () => {
    const current = generationRun("current", "current context");
    const previous = generationRun("previous", "previous context");

    expect(generationRunsForResearch(
      [previous, current],
      "current context",
    ).map((run) => run.id)).toEqual(["current"]);
  });
});

function generationRun(
  id: string,
  researchContext: string,
): GeoQueryGenerationRunResource {
  return {
    id,
    projectId: "project-1",
    provider: "gemini",
    status: "completed",
    requestPayload: { researchContext },
    errorCode: null,
    errorMessage: null,
    createdAt: "2026-07-19T02:00:00Z",
    completedAt: "2026-07-19T02:00:00Z",
    drafts: [],
  };
}

function draft(
  id: string,
  selectionStatus: GeoQueryDraftResource["selectionStatus"],
  acceptedQueryId: string | null,
): GeoQueryDraftResource {
  return {
    id,
    generationRunId: "generation-1",
    projectId: "project-1",
    topicId: null,
    topicName: "採購",
    queryText: id,
    keywords: [],
    region: "TW",
    language: "zh-TW",
    marketType: "b2b_procurement",
    intent: null,
    isBranded: false,
    status: "draft",
    selectionStatus,
    acceptedQueryId,
    metadata: {},
    createdAt: "2026-07-19T00:00:00Z",
    updatedAt: "2026-07-19T00:00:00Z",
  };
}
