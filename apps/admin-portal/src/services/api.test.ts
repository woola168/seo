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
});
