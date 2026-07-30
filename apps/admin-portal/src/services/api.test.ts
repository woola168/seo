import { beforeEach, describe, expect, it, vi } from "vitest";

const dashboardReportBody = {
  periodStart: "2026-06-01T00:00:00Z",
  periodEnd: "2026-06-30T23:59:59Z",
  comparisonStart: "2026-05-01T00:00:00Z",
  comparisonEnd: "2026-05-31T23:59:59Z",
  overview: [],
  entities: [],
  citationUrls: [],
  citationDomains: [],
  sentiments: [],
};

describe("api.geoAnalysis.dashboardReport", () => {
  beforeEach(() => {
    vi.resetModules();
    vi.unstubAllEnvs();
    vi.stubEnv("VITE_API_BASE_URL", "");
    const store = new Map<string, string>();
    vi.stubGlobal("sessionStorage", {
      getItem: (key: string) => store.get(key) ?? null,
      setItem: (key: string, value: string) => store.set(key, value),
      removeItem: (key: string) => store.delete(key),
      clear: () => store.clear(),
    });
  });

  it("loads the persisted GEO Platform catalog", async () => {
    let requestedPath = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        requestedPath = String(path);
        return {
          ok: true,
          status: 200,
          json: async () => ({ items: [], total: 0 }),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.geoAnalysis.platforms();

    expect(requestedPath).toBe("/api/geo/platforms");
  });

  it("posts Project inspection inputs without market research settings", async () => {
    let requestedPath = "";
    let requestedBody = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
        requestedPath = String(path);
        requestedBody = String(init?.body ?? "");
        return {
          ok: true,
          status: 200,
          json: async () => ({
            sourceUrl: "https://www.kaiser.com.tw/",
            retrievedUrl: "https://www.kaiser.com.tw/",
            projectName: "港香蘭藥廠股份有限公司",
            projectDescription: "位於台灣的中藥製藥公司。",
            projectType: "company",
            coreOfferings: ["科學中藥"],
          }),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.inspectGeoProject({
      projectUrl: "https://www.kaiser.com.tw/",
      language: "zh-TW",
    });

    expect(requestedPath).toBe(
      "/api/v1/geo-tracking/project-discovery/inspection",
    );
    expect(JSON.parse(requestedBody)).toEqual({
      projectUrl: "https://www.kaiser.com.tw/",
      language: "zh-TW",
    });
  });

  it("posts confirmed Project identity to the suggestions endpoint", async () => {
    let requestedPath = "";
    let requestedBody = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
        requestedPath = String(path);
        requestedBody = String(init?.body ?? "");
        return {
          ok: true,
          status: 200,
          json: async () => ({
            competitors: [],
            topics: [],
            keywords: [],
            references: [],
          }),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.suggestGeoProject({
      confirmedProject: {
        sourceUrl: "https://www.kaiser.com.tw/",
        retrievedUrl: "https://www.kaiser.com.tw/",
        projectName: "港香蘭",
        projectDescription: "提供科學中藥產品。",
        projectType: "company",
        coreOfferings: ["科學中藥"],
      },
      region: "TW",
      language: "zh-TW",
      marketType: "b2c",
      competitorCount: 5,
      topicCount: 5,
      keywordCount: 5,
    });

    expect(requestedPath).toBe(
      "/api/v1/geo-tracking/project-discovery/suggestions",
    );
    expect(JSON.parse(requestedBody)).toMatchObject({
      confirmedProject: {
        projectName: "港香蘭",
        projectDescription: "提供科學中藥產品。",
      },
      region: "TW",
      competitorCount: 5,
    });
    expect(JSON.parse(requestedBody)).not.toHaveProperty("audience");
    expect(JSON.parse(requestedBody).confirmedProject).not.toHaveProperty(
      "targetAudiences",
    );
  });

  it("requests the dashboard report endpoint with camelCase query params", async () => {
    let requestedPath = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        requestedPath = String(path);
        return {
          ok: true,
          status: 200,
          json: async () => dashboardReportBody,
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.geoAnalysis.dashboardReport("project-1", {
      periodStart: "2026-06-01T00:00:00Z",
      periodEnd: "2026-06-30T23:59:59Z",
      comparisonStart: "2026-05-01T00:00:00Z",
      comparisonEnd: "2026-05-31T23:59:59Z",
      queryId: "query-1",
      topicId: "",
      provider: "gemini",
      region: "TW",
      language: "zh-TW",
    });

    const url = new URL(requestedPath, "https://portal.example");
    expect(url.pathname).toBe("/api/geo/projects/project-1/reports/dashboard");
    expect(url.searchParams.get("periodStart")).toBe("2026-06-01T00:00:00Z");
    expect(url.searchParams.get("periodEnd")).toBe("2026-06-30T23:59:59Z");
    expect(url.searchParams.get("comparisonStart")).toBe(
      "2026-05-01T00:00:00Z",
    );
    expect(url.searchParams.get("comparisonEnd")).toBe(
      "2026-05-31T23:59:59Z",
    );
    expect(url.searchParams.get("queryId")).toBe("query-1");
    expect(url.searchParams.has("topicId")).toBe(false);
    expect(url.searchParams.get("provider")).toBe("gemini");
    expect(url.searchParams.get("region")).toBe("TW");
    expect(url.searchParams.get("language")).toBe("zh-TW");
  });

  it("serializes Overview multi-select filters as repeated query params", async () => {
    let requestedPath = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        requestedPath = String(path);
        return {
          ok: true,
          status: 200,
          json: async () => ({}),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.geoAnalysis.overviewReport("project-1", {
      periodStart: "2026-07-01T00:00:00Z",
      periodEnd: "2026-07-08T00:00:00Z",
      topicIds: ["topic-1", "topic-2"],
      providers: ["gemini", "google_aio"],
      metadataIndustry: ["保健"],
      metadataType: ["品牌提及", "資訊引用"],
      timeZone: "Asia/Taipei",
    });

    const url = new URL(requestedPath, "https://portal.example");
    expect(url.pathname).toBe("/api/geo/projects/project-1/reports/overview");
    expect(url.searchParams.getAll("topicIds")).toEqual(["topic-1", "topic-2"]);
    expect(url.searchParams.getAll("providers")).toEqual(["gemini", "google_aio"]);
    expect(url.searchParams.getAll("metadataType")).toEqual(["品牌提及", "資訊引用"]);
  });

  it("requests the KMindHub workspace mapping endpoint", async () => {
    let requestedPath = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        requestedPath = String(path);
        return {
          ok: true,
          status: 200,
          json: async () => ({
            id: "mapping-1",
            tenantId: "tenant-1",
            workspaceId: "workspace-1",
            displayName: "Demo Workspace",
            provisioningMode: "manual",
            status: "active",
            createdAt: "2026-01-01T00:00:00Z",
            updatedAt: "2026-01-01T00:00:00Z",
          }),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.geoAnalysis.kmindhubWorkspace();

    expect(requestedPath).toBe("/api/geo/integrations/kmindhub/workspace");
  });

  it("requests project-scoped setup list endpoints", async () => {
    const requestedPaths: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        requestedPaths.push(String(path));
        return {
          ok: true,
          status: 200,
          json: async () => ({ items: [], total: 0 }),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await Promise.all([
      api.geoAnalysis.projectAliases("project-1"),
      api.geoAnalysis.projectQueryPlatforms("project-1"),
    ]);

    expect(requestedPaths).toEqual([
      "/api/geo/projects/project-1/entity-aliases",
      "/api/geo/projects/project-1/query-platforms",
    ]);
  });

  it("requests run result semantic analysis endpoint", async () => {
    let requestedPath = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        requestedPath = String(path);
        return {
          ok: true,
          status: 200,
          json: async () => ({
            runResultId: "result-1",
            analyzer: "fake",
            analyzerVersion: "v1",
            status: "completed",
            entityMentions: [],
            sentiments: [],
            semanticFacts: [],
            errorCode: null,
            errorMessage: null,
          }),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.geoAnalysis.runResultSemanticAnalysis("result-1");

    expect(requestedPath).toBe("/api/geo/run-results/result-1/semantic-analysis");
  });

  it("prefixes API requests with VITE_API_BASE_URL when configured", async () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://titan.younilab.com");
    let requestedPath = "";
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        requestedPath = String(path);
        return {
          ok: true,
          status: 200,
          json: async () => ({ items: [] }),
        } as Response;
      }),
    );
    const { api } = await import("./api");

    await api.geoAnalysis.projects();

    expect(requestedPath).toBe("https://titan.younilab.com/api/geo/projects");
  });

  it("refreshes the access token once and retries a 401 request", async () => {
    sessionStorage.setItem("accessToken", "expired-token");
    const authorizationHeaders: string[] = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
        const pathname = String(path);
        const headers = new Headers(init?.headers);
        if (pathname === "/api/me") {
          authorizationHeaders.push(headers.get("Authorization") ?? "");
          if (authorizationHeaders.length === 1) {
            return {
              ok: false,
              status: 401,
              json: async () => ({ detail: "Authentication required" }),
            } as Response;
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({ id: "user-1", email: "admin@example.com" }),
          } as Response;
        }
        if (pathname === "/api/auth/refresh") {
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessToken: "fresh-token" }),
          } as Response;
        }
        throw new Error(`unexpected request: ${pathname}`);
      }),
    );
    const { api } = await import("./api");

    await api.me();

    expect(authorizationHeaders).toEqual([
      "Bearer expired-token",
      "Bearer fresh-token",
    ]);
    expect(sessionStorage.getItem("accessToken")).toBe("fresh-token");
  });

  it("shares one refresh request across concurrent 401 responses", async () => {
    sessionStorage.setItem("accessToken", "expired-token");
    let refreshCalls = 0;
    let meCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        const pathname = String(path);
        if (pathname === "/api/me") {
          meCalls += 1;
          if (meCalls <= 2) {
            return {
              ok: false,
              status: 401,
              json: async () => ({ detail: "Authentication required" }),
            } as Response;
          }
          return {
            ok: true,
            status: 200,
            json: async () => ({ id: "user-1", email: "admin@example.com" }),
          } as Response;
        }
        if (pathname === "/api/auth/refresh") {
          refreshCalls += 1;
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessToken: "fresh-token" }),
          } as Response;
        }
        throw new Error(`unexpected request: ${pathname}`);
      }),
    );
    const { api } = await import("./api");

    await Promise.all([api.me(), api.me()]);

    expect(refreshCalls).toBe(1);
    expect(meCalls).toBe(4);
  });

  it("clears the access token when refresh fails", async () => {
    sessionStorage.setItem("accessToken", "expired-token");
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        const pathname = String(path);
        if (pathname === "/api/me" || pathname === "/api/auth/refresh") {
          return {
            ok: false,
            status: 401,
            json: async () => ({ detail: "Authentication required" }),
          } as Response;
        }
        throw new Error(`unexpected request: ${pathname}`);
      }),
    );
    const { api } = await import("./api");

    await expect(api.me()).rejects.toMatchObject({ status: 401 });

    expect(sessionStorage.getItem("accessToken")).toBeNull();
  });

  it("does not refresh a forbidden response", async () => {
    sessionStorage.setItem("accessToken", "valid-token");
    let refreshCalls = 0;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL) => {
        const pathname = String(path);
        if (pathname === "/api/me") {
          return {
            ok: false,
            status: 403,
            json: async () => ({ detail: "Access denied" }),
          } as Response;
        }
        if (pathname === "/api/auth/refresh") {
          refreshCalls += 1;
          return {
            ok: true,
            status: 200,
            json: async () => ({ accessToken: "fresh-token" }),
          } as Response;
        }
        throw new Error(`unexpected request: ${pathname}`);
      }),
    );
    const { api } = await import("./api");

    await expect(api.me()).rejects.toMatchObject({ status: 403 });

    expect(refreshCalls).toBe(0);
    expect(sessionStorage.getItem("accessToken")).toBe("valid-token");
  });

  it("uses the Project Query Settings and status subresources", async () => {
    const requests: Array<{ path: string; method: string; body: unknown }> = [];
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
        requests.push({
          path: String(path),
          method: init?.method ?? "GET",
          body: init?.body ? JSON.parse(String(init.body)) : null,
        });
        const isStatus = String(path).endsWith("/status");
        return {
          ok: true,
          status: 200,
          json: async () => isStatus
            ? { projectId: "project-1", status: "paused", updatedAt: "2026-07-19T00:00:00Z" }
            : {
                projectId: "project-1",
                researchProvider: "gemini",
                runProvider: "gemini",
                keywords: ["ERP"],
                marketType: "b2b_procurement",
                maxQueries: 8,
                audience: { name: "採購", description: "採購主管" },
                intents: [
                  { category: "commercial_investigation", description: "比較供應商" },
                  { category: "transactional", description: "尋找詢價方式" },
                ],
                shouldMentionOwnBrand: true,
                shouldMentionCompetitor: false,
                updatedAt: "2026-07-19T00:00:00Z",
              },
        } as Response;
      }),
    );
    const { api } = await import("./api");
    const settings = {
      researchProvider: "gemini" as const,
      runProvider: "gemini" as const,
      keywords: ["ERP"],
      marketType: "b2b_procurement" as const,
      maxQueries: 8,
      audience: { name: "採購", description: "採購主管" },
      intents: [
        { category: "commercial_investigation", description: "比較供應商" },
        { category: "transactional", description: "尋找詢價方式" },
      ],
      shouldMentionOwnBrand: true,
      shouldMentionCompetitor: false,
    };

    await api.geoAnalysis.querySettings("project-1");
    await api.geoAnalysis.updateQuerySettings("project-1", settings);
    await api.geoAnalysis.updateProjectStatus("project-1", { status: "paused" });

    expect(requests).toEqual([
      {
        path: "/api/geo/projects/project-1/query-settings",
        method: "GET",
        body: null,
      },
      {
        path: "/api/geo/projects/project-1/query-settings",
        method: "PUT",
        body: settings,
      },
      {
        path: "/api/geo/projects/project-1/status",
        method: "PATCH",
        body: { status: "paused" },
      },
    ]);
  });

  it("returns the daily-slot creation result when creating a GEO job", async () => {
    const fetchMock = vi.fn(async (_path: RequestInfo | URL, init?: RequestInit) => ({
      ok: true,
      status: 200,
      json: async () => ({ id: "job-1", wasCreated: false }),
      requestMethod: init?.method,
    }) as Response);
    vi.stubGlobal("fetch", fetchMock);
    const { api } = await import("./api");

    const result = await api.geoAnalysis.createJob("query-1", {
      platformId: "gemini-1",
      scheduledFor: null,
      priority: "normal",
      jobType: "manual_run",
    });

    expect(result.wasCreated).toBe(false);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/geo/queries/query-1/jobs",
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({
          platformId: "gemini-1",
          scheduledFor: null,
          priority: "normal",
          jobType: "manual_run",
        }),
      }),
    );
  });

  it("loads persisted Query Research and Generation runs", async () => {
    const fetchMock = vi.fn(async () => ({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0 }),
    }) as Response);
    vi.stubGlobal("fetch", fetchMock);
    const { api } = await import("./api");

    await api.geoAnalysis.queryResearchRuns("project-1");
    await api.geoAnalysis.queryResearchRun("research-1");
    await api.geoAnalysis.queryGenerationRuns("project-1");
    await api.geoAnalysis.queryGenerationRun("generation-1");

    expect(fetchMock.mock.calls.map(([path]) => path)).toEqual([
      "/api/geo/projects/project-1/query-research-runs",
      "/api/geo/query-research-runs/research-1",
      "/api/geo/projects/project-1/query-generation-runs",
      "/api/geo/query-generation-runs/generation-1",
    ]);
  });

  it("replaces all aliases for an Entity with one PUT request", async () => {
    let requestedPath = "";
    let requestedInit: RequestInit | undefined;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: RequestInfo | URL, init?: RequestInit) => {
        requestedPath = String(path);
        requestedInit = init;
        return {
          ok: true,
          status: 200,
          json: async () => ({ items: [], total: 0 }),
        } as Response;
      }),
    );
    const { api } = await import("./api");
    const input = {
      items: [
        { alias: "品牌別名", matchType: "exact" as const },
        { alias: "Brand", matchType: "contains" as const },
      ],
    };

    await api.geoAnalysis.replaceAliases("entity-1", input);

    expect(requestedPath).toBe("/api/geo/entities/entity-1/aliases");
    expect(requestedInit?.method).toBe("PUT");
    expect(JSON.parse(String(requestedInit?.body))).toEqual(input);
  });

  it("keeps RFC 7807 invalidParams on ApiError", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => ({
        ok: false,
        status: 422,
        json: async () => ({
          detail: "validation failed",
          invalidParams: [{ name: "body.maxQueries", reason: "must be less than 40", type: "less_than_equal" }],
        }),
      }) as Promise<Response>),
    );
    const { api } = await import("./api");

    await expect(api.geoAnalysis.updateQuerySettings("project-1", {
      researchProvider: "gemini",
      runProvider: "gemini",
      keywords: [],
      marketType: "b2c",
      maxQueries: 41,
      audience: { name: "採購", description: "採購主管" },
      intents: [
        { category: "commercial_investigation", description: "比較供應商" },
      ],
      shouldMentionOwnBrand: true,
      shouldMentionCompetitor: false,
    })).rejects.toMatchObject({
      status: 422,
      invalidParams: [{ name: "body.maxQueries", reason: "must be less than 40" }],
    });
  });
});
