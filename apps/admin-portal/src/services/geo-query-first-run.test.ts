import { afterEach, beforeAll, describe, expect, it, vi } from "vitest";
import type {
  GeoJobCreationResource,
  GeoJobResource,
  GeoPlatformResource,
  GeoQueryDraftResource,
  GeoQueryResource,
} from "../types";

let service: typeof import("./geo-query-first-run");
let apiModule: typeof import("./api");

beforeAll(async () => {
  vi.stubGlobal("sessionStorage", {
    getItem: () => null,
    setItem: () => undefined,
    removeItem: () => undefined,
    clear: () => undefined,
  });
  service = await import("./geo-query-first-run");
  apiModule = await import("./api");
});

afterEach(() => vi.restoreAllMocks());

const query = {
  id: "query-1",
  projectId: "project-1",
  topicId: null,
  queryText: "推薦 ERP 系統",
  region: "TW",
  language: "zh-TW",
  marketType: "b2b_procurement",
  intent: null,
  buyerStage: null,
  isBranded: false,
  priority: "normal",
  status: "active",
  metadata: {},
  createdAt: "2026-07-19T00:00:00Z",
  updatedAt: "2026-07-19T00:00:00Z",
} satisfies GeoQueryResource;

const platforms = [
  {
    id: "gemini-1",
    code: "gemini",
    displayName: "Gemini",
    providerType: "google",
    defaultModel: "gemini-3.1-flash-lite",
    status: "active",
  },
  {
    id: "chatgpt-1",
    code: "chatgpt",
    displayName: "ChatGPT",
    providerType: "openai",
    defaultModel: "gpt-5",
    status: "active",
  },
  {
    id: "paused-1",
    code: "paused",
    displayName: "Paused Platform",
    providerType: "other",
    defaultModel: null,
    status: "paused",
  },
] satisfies GeoPlatformResource[];

function job(
  wasCreated: boolean,
  status: GeoJobResource["status"] = "pending",
  overrides: Partial<GeoJobCreationResource> = {},
): GeoJobCreationResource {
  return {
    id: "job-1",
    projectId: "project-1",
    queryId: query.id,
    platformId: "gemini-1",
    batchId: null,
    scheduleId: null,
    source: "manual",
    jobType: "query_research_first_run",
    priority: "normal",
    scheduledFor: "2026-07-19T00:00:00Z",
    status,
    attemptCount: 0,
    maxAttempts: 3,
    dedupeKey: "daily-key",
    externalRunId: null,
    lastErrorMessage: null,
    dispatchBackend: null,
    dispatchMessageId: null,
    lastErrorCode: null,
    createdAt: "2026-07-19T00:00:00Z",
    updatedAt: "2026-07-19T00:00:00Z",
    wasCreated,
    ...overrides,
  };
}

function mockPlatforms(items: GeoPlatformResource[] = platforms): void {
  vi.spyOn(apiModule.api.geoAnalysis, "platforms").mockResolvedValue({
    items,
    total: items.length,
  });
}

function draft(id: string, acceptedQueryId: string | null): GeoQueryDraftResource {
  return {
    id,
    generationRunId: "generation-1",
    projectId: "project-1",
    topicId: null,
    topicName: "ERP",
    queryText: `Query ${id}`,
    keywords: [],
    region: "TW",
    language: "zh-TW",
    marketType: "b2b_procurement",
    intent: null,
    isBranded: false,
    status: "draft",
    selectionStatus: acceptedQueryId ? "accepted" : "shortlisted",
    acceptedQueryId,
    metadata: {},
    createdAt: "2026-07-19T00:00:00Z",
    updatedAt: "2026-07-19T00:00:00Z",
  };
}

describe("GEO Query first run", () => {
  it("creates and dispatches one job for every active Platform", async () => {
    mockPlatforms();
    vi.spyOn(apiModule.api.geoAnalysis, "createJob").mockImplementation(
      async (_, input) => job(true, "pending", { id: `job-${input.platformId}`, platformId: input.platformId }),
    );
    const dispatch = vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob").mockImplementation(
      async (jobId) => job(true, "published", { id: jobId }),
    );

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result).toMatchObject({
      combinations: 2,
      dispatched: 2,
      alreadyReserved: 0,
      retryScheduled: 0,
      failures: [],
    });
    expect(apiModule.api.geoAnalysis.createJob).toHaveBeenCalledTimes(2);
    expect(apiModule.api.geoAnalysis.createJob).toHaveBeenNthCalledWith(1, query.id, {
      platformId: "gemini-1",
      scheduledFor: null,
      priority: "normal",
      jobType: "query_research_first_run",
    });
    expect(apiModule.api.geoAnalysis.createJob).toHaveBeenNthCalledWith(2, query.id, {
      platformId: "chatgpt-1",
      scheduledFor: null,
      priority: "normal",
      jobType: "query_research_first_run",
    });
    expect(dispatch).toHaveBeenCalledTimes(2);
  });

  it("dispatches an existing pending first-run job", async () => {
    mockPlatforms([platforms[0]]);
    vi.spyOn(apiModule.api.geoAnalysis, "createJob").mockResolvedValue(job(false));
    const dispatch = vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob").mockResolvedValue(job(false, "published"));

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result.dispatched).toBe(1);
    expect(result.alreadyReserved).toBe(0);
    expect(dispatch).toHaveBeenCalledWith("job-1");
  });

  it("leaves an existing delayed first-run job for scheduler retry", async () => {
    mockPlatforms([platforms[0]]);
    vi.spyOn(apiModule.api.geoAnalysis, "createJob").mockResolvedValue(job(false, "delayed"));
    const dispatch = vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob");

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result.retryScheduled).toBe(1);
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("does not dispatch an existing terminal or ordinary manual job", async () => {
    mockPlatforms([platforms[0]]);
    vi.spyOn(apiModule.api.geoAnalysis, "createJob").mockResolvedValue(
      job(false, "failed", { jobType: "manual_run" }),
    );
    const dispatch = vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob");

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result.alreadyReserved).toBe(1);
    expect(dispatch).not.toHaveBeenCalled();
  });

  it("continues other Platforms when one Job creation fails", async () => {
    mockPlatforms();
    vi.spyOn(apiModule.api.geoAnalysis, "createJob")
      .mockRejectedValueOnce(new Error("create failed"))
      .mockResolvedValueOnce(job(true, "pending", { platformId: "chatgpt-1" }));
    vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob").mockResolvedValue(job(true, "published"));

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result).toMatchObject({ combinations: 2, dispatched: 1 });
    expect(result.failures).toEqual(["推薦 ERP 系統／Gemini：create failed"]);
  });

  it("reports delayed or lost dispatch responses as backend retries", async () => {
    mockPlatforms();
    vi.spyOn(apiModule.api.geoAnalysis, "createJob")
      .mockResolvedValueOnce(job(true))
      .mockResolvedValueOnce(job(true, "pending", { id: "job-2", platformId: "chatgpt-1" }));
    vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob")
      .mockResolvedValueOnce(job(true, "delayed"))
      .mockRejectedValueOnce(new Error("network lost"));

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result).toMatchObject({ dispatched: 0, retryScheduled: 2, failures: [] });
  });

  it("keeps a pending dispatch response under backend retry", async () => {
    mockPlatforms([platforms[0]]);
    vi.spyOn(apiModule.api.geoAnalysis, "createJob").mockResolvedValue(job(true));
    vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob").mockResolvedValue(job(true, "pending"));

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result).toMatchObject({ dispatched: 0, retryScheduled: 1, failures: [] });
  });

  it.each([
    ["failed", "publish failed"],
    ["cancelled", null],
  ] as const)("reports a %s dispatch response as a failure", async (status, lastErrorMessage) => {
    mockPlatforms([platforms[0]]);
    vi.spyOn(apiModule.api.geoAnalysis, "createJob").mockResolvedValue(job(true));
    vi.spyOn(apiModule.api.geoAnalysis, "dispatchJob").mockResolvedValue(
      job(true, status, { lastErrorMessage }),
    );

    const result = await service.runAcceptedQueriesOnce([query]);

    expect(result.dispatched).toBe(0);
    expect(result.retryScheduled).toBe(0);
    expect(result.failures).toEqual([
      `推薦 ERP 系統／Gemini：${lastErrorMessage || `首次數據 Job ${status}`}`,
    ]);
  });

  it("does not create jobs when no active Platform exists", async () => {
    mockPlatforms([platforms[2]]);
    const createJob = vi.spyOn(apiModule.api.geoAnalysis, "createJob");

    await expect(service.runAcceptedQueriesOnce([query])).rejects.toThrow(
      "沒有可用的 Platform",
    );
    expect(createJob).not.toHaveBeenCalled();
  });
});

describe("accepted Query reconciliation", () => {
  it("recovers accepted Queries after an Accept response is lost and deduplicates known Queries", async () => {
    const recoveredQuery = { ...query, id: "query-2", queryText: "ERP 導入方式" };
    vi.spyOn(apiModule.api.geoAnalysis, "queries").mockResolvedValue({
      items: [query, recoveredQuery],
      total: 2,
    });

    const result = await service.reconcileAcceptedQueries(
      "project-1",
      ["draft-1", "draft-2"],
      [draft("draft-1", query.id), draft("draft-2", recoveredQuery.id)],
      [query],
    );

    expect(result.queries.map((item) => item.id)).toEqual([query.id, recoveredQuery.id]);
    expect(result.reconciledDraftIds).toEqual(["draft-1", "draft-2"]);
    expect(apiModule.api.geoAnalysis.queries).toHaveBeenCalledWith("project-1");
  });

  it("keeps unresolved drafts failed when the accepted Query is absent", async () => {
    vi.spyOn(apiModule.api.geoAnalysis, "queries").mockResolvedValue({ items: [], total: 0 });

    const result = await service.reconcileAcceptedQueries(
      "project-1",
      ["draft-1"],
      [draft("draft-1", "query-missing")],
      [],
    );

    expect(result.queries).toEqual([]);
    expect(result.reconciledDraftIds).toEqual([]);
  });
});
