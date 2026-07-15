import { beforeEach, describe, expect, it, vi } from "vitest";
import {
  useGeoProjectWorkspace,
  type GeoWorkspaceProfile,
} from "./geo-project-workspace";

const apiMocks = vi.hoisted(() => ({
  customers: vi.fn(),
  tasks: vi.fn(),
  projects: vi.fn(),
  entities: vi.fn(),
  aliases: vi.fn(),
  projectAliases: vi.fn(),
  topics: vi.fn(),
  queries: vi.fn(),
  queryPlatforms: vi.fn(),
  projectQueryPlatforms: vi.fn(),
  schedules: vi.fn(),
  projectSchedules: vi.fn(),
  jobs: vi.fn(),
  runResults: vi.fn(),
}));

vi.mock("../services/api", () => ({
  api: {
    customers: apiMocks.customers,
    tasks: apiMocks.tasks,
    geoAnalysis: {
      projects: apiMocks.projects,
      entities: apiMocks.entities,
      aliases: apiMocks.aliases,
      projectAliases: apiMocks.projectAliases,
      topics: apiMocks.topics,
      queries: apiMocks.queries,
      queryPlatforms: apiMocks.queryPlatforms,
      projectQueryPlatforms: apiMocks.projectQueryPlatforms,
      schedules: apiMocks.schedules,
      projectSchedules: apiMocks.projectSchedules,
      jobs: apiMocks.jobs,
      runResults: apiMocks.runResults,
    },
  },
}));

const project = {
  id: "project-1",
  customerId: null,
  seoTaskId: null,
  name: "Project 1",
  defaultRegion: "TW",
  defaultLanguage: "zh-TW",
  status: "active",
  dailyRunBudget: 100,
  createdAt: "2026-07-01T00:00:00Z",
  updatedAt: "2026-07-01T00:00:00Z",
};

function createStorage(): Storage {
  const values = new Map<string, string>();
  return {
    get length() {
      return values.size;
    },
    clear: () => values.clear(),
    getItem: (key) => values.get(key) ?? null,
    key: (index) => Array.from(values.keys())[index] ?? null,
    removeItem: (key) => values.delete(key),
    setItem: (key, value) => values.set(key, value),
  };
}

function collection(items: unknown[] = []) {
  return Promise.resolve({ items, total: items.length });
}

describe("useGeoProjectWorkspace", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    vi.stubGlobal("localStorage", createStorage());
    apiMocks.customers.mockReturnValue(collection());
    apiMocks.tasks.mockReturnValue(collection());
    apiMocks.projects.mockReturnValue(collection([project]));
    apiMocks.entities.mockReturnValue(collection());
    apiMocks.projectAliases.mockReturnValue(collection());
    apiMocks.topics.mockReturnValue(collection());
    apiMocks.queries.mockReturnValue(collection());
    apiMocks.projectQueryPlatforms.mockReturnValue(collection());
    apiMocks.projectSchedules.mockReturnValue(collection());
    apiMocks.jobs.mockReturnValue(collection());
  });

  it.each<{
    profile: GeoWorkspaceProfile;
    expected: string[];
  }>([
    { profile: "projects", expected: ["customers", "tasks"] },
    { profile: "entities", expected: ["entities", "projectAliases"] },
    { profile: "topics-queries", expected: ["topics", "queries"] },
    {
      profile: "platforms-schedules",
      expected: ["queries", "projectQueryPlatforms", "projectSchedules"],
    },
    { profile: "run-jobs", expected: ["queries", "jobs"] },
  ])("loads only the $profile profile resources", async ({ profile, expected }) => {
    const workspace = useGeoProjectWorkspace(profile);

    await workspace.loadProjects();
    if (profile !== "projects") {
      await vi.waitFor(() => {
        for (const name of expected) {
          expect(apiMocks[name as keyof typeof apiMocks]).toHaveBeenCalled();
        }
      });
    }

    const detailCalls = [
      "entities",
      "projectAliases",
      "topics",
      "queries",
      "projectQueryPlatforms",
      "projectSchedules",
      "jobs",
    ] as const;
    for (const name of detailCalls) {
      expect(apiMocks[name]).toHaveBeenCalledTimes(expected.includes(name) ? 1 : 0);
    }
    expect(apiMocks.customers).toHaveBeenCalledTimes(expected.includes("customers") ? 1 : 0);
    expect(apiMocks.tasks).toHaveBeenCalledTimes(expected.includes("tasks") ? 1 : 0);
    expect(apiMocks.aliases).not.toHaveBeenCalled();
    expect(apiMocks.queryPlatforms).not.toHaveBeenCalled();
    expect(apiMocks.schedules).not.toHaveBeenCalled();
    expect(apiMocks.runResults).not.toHaveBeenCalled();
  });

  it("keeps entities when aliases fail and clears the error after a successful refresh", async () => {
    apiMocks.entities.mockReturnValue(collection([
      { id: "entity-1", projectId: "project-1", name: "Entity 1" },
    ]));
    apiMocks.projectAliases.mockRejectedValue(new Error("aliases unavailable"));
    const workspace = useGeoProjectWorkspace("entities");

    await workspace.loadProjects();
    await vi.waitFor(() => expect(workspace.entities.value[0]?.id).toBe("entity-1"));

    expect(workspace.aliases.value).toEqual([]);
    expect(workspace.errorMessage.value).toBe(
      "部分資料載入失敗：Aliases。請稍後重新整理。",
    );

    apiMocks.projectAliases.mockReturnValue(collection([
      { id: "alias-1", entityId: "entity-1", alias: "Entity One" },
    ]));
    await workspace.refreshProjectDetails();

    expect(workspace.aliases.value[0]?.id).toBe("alias-1");
    expect(workspace.errorMessage.value).toBe("");
  });

  it("keeps queries and schedules when query platforms fail", async () => {
    apiMocks.queries.mockReturnValue(collection([
      { id: "query-1", projectId: "project-1", queryText: "Query 1" },
    ]));
    apiMocks.projectQueryPlatforms.mockRejectedValue(new Error("platforms unavailable"));
    apiMocks.projectSchedules.mockReturnValue(collection([
      { id: "schedule-1", queryId: "query-1", platformId: "platform-1" },
    ]));
    const workspace = useGeoProjectWorkspace("platforms-schedules");

    await workspace.loadProjects();
    await vi.waitFor(() => expect(workspace.schedules.value[0]?.id).toBe("schedule-1"));

    expect(workspace.queries.value[0]?.id).toBe("query-1");
    expect(workspace.queryPlatforms.value).toEqual([]);
    expect(workspace.errorMessage.value).toBe(
      "部分資料載入失敗：Query Platforms。請稍後重新整理。",
    );
  });

  it("lists every failed profile resource in request order", async () => {
    apiMocks.projectQueryPlatforms.mockRejectedValue(new Error("platforms unavailable"));
    apiMocks.projectSchedules.mockRejectedValue(new Error("schedules unavailable"));
    const workspace = useGeoProjectWorkspace("platforms-schedules");

    await workspace.loadProjects();
    await vi.waitFor(() => {
      expect(workspace.errorMessage.value).toBe(
        "部分資料載入失敗：Query Platforms、Schedules。請稍後重新整理。",
      );
    });
  });

  it("does not let an older project request overwrite the current project", async () => {
    let resolveFirstEntities: ((value: { items: unknown[]; total: number }) => void) | undefined;
    apiMocks.projects.mockReturnValue(collection([
      project,
      { ...project, id: "project-2", name: "Project 2" },
    ]));
    apiMocks.entities.mockImplementation((projectId: string) => {
      if (projectId === "project-1") {
        return new Promise((resolve) => {
          resolveFirstEntities = resolve;
        });
      }
      return collection([{ id: "entity-2", projectId: "project-2" }]);
    });

    const workspace = useGeoProjectWorkspace("entities");
    await workspace.loadProjects();
    await vi.waitFor(() => expect(apiMocks.entities).toHaveBeenCalledWith("project-1"));
    workspace.selectedProjectId.value = "project-2";
    await vi.waitFor(() => expect(workspace.entities.value[0]?.id).toBe("entity-2"));

    resolveFirstEntities?.({ items: [{ id: "entity-1", projectId: "project-1" }], total: 1 });
    await Promise.resolve();

    expect(workspace.entities.value[0]?.id).toBe("entity-2");
  });
});
