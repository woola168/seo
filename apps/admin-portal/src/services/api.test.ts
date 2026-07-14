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
});
