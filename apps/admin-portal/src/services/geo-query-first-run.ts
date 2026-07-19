import { api } from "./api";
import type {
  GeoJobCreationResource,
  GeoPlatformResource,
  GeoQueryDraftResource,
  GeoQueryResource,
} from "../types";

export interface GeoQueryFirstRunSummary {
  combinations: number;
  dispatched: number;
  alreadyReserved: number;
  retryScheduled: number;
  failures: string[];
}

export interface AcceptedQueryReconciliation {
  queries: GeoQueryResource[];
  reconciledDraftIds: string[];
}

export async function reconcileAcceptedQueries(
  projectId: string,
  selectedDraftIds: readonly string[],
  drafts: readonly GeoQueryDraftResource[],
  acceptedQueries: readonly GeoQueryResource[],
): Promise<AcceptedQueryReconciliation> {
  const queriesById = new Map(acceptedQueries.map((query) => [query.id, query]));
  const selectedIds = new Set(selectedDraftIds);
  const acceptedDrafts = drafts.filter(
    (draft) => selectedIds.has(draft.id) && Boolean(draft.acceptedQueryId),
  );
  const missingQueryIds = acceptedDrafts
    .map((draft) => draft.acceptedQueryId)
    .filter((queryId): queryId is string => queryId !== null && !queriesById.has(queryId));

  if (missingQueryIds.length) {
    const projectQueries = await api.geoAnalysis.queries(projectId);
    const missingIds = new Set(missingQueryIds);
    for (const query of projectQueries.items) {
      if (missingIds.has(query.id)) queriesById.set(query.id, query);
    }
  }

  return {
    queries: [...queriesById.values()],
    reconciledDraftIds: acceptedDrafts
      .filter((draft) => draft.acceptedQueryId && queriesById.has(draft.acceptedQueryId))
      .map((draft) => draft.id),
  };
}

export async function runAcceptedQueriesOnce(
  queries: readonly GeoQueryResource[],
): Promise<GeoQueryFirstRunSummary> {
  const platforms = await api.geoAnalysis.platforms();
  const activePlatforms = platforms.items.filter((platform) => platform.status === "active");
  if (!activePlatforms.length) {
    throw new Error("目前沒有可用的 Platform，Query 已建立但無法派送首次數據。");
  }

  const summary: GeoQueryFirstRunSummary = {
    combinations: queries.length * activePlatforms.length,
    dispatched: 0,
    alreadyReserved: 0,
    retryScheduled: 0,
    failures: [],
  };
  for (const query of queries) {
    for (const platform of activePlatforms) {
      await runQueryOnPlatform(query, platform, summary);
    }
  }
  return summary;
}

async function runQueryOnPlatform(
  query: GeoQueryResource,
  platform: GeoPlatformResource,
  summary: GeoQueryFirstRunSummary,
): Promise<void> {
  let creation: GeoJobCreationResource;
  try {
    creation = await api.geoAnalysis.createJob(query.id, {
      platformId: platform.id,
      scheduledFor: null,
      priority: query.priority,
      jobType: "query_research_first_run",
    });
  } catch (error) {
    summary.failures.push(
      `${query.queryText}／${platform.displayName}：${error instanceof Error ? error.message : "首次數據 Job 建立失敗"}`,
    );
    return;
  }

  if (!creation.wasCreated) {
    if (creation.jobType === "query_research_first_run" && creation.status === "pending") {
      await dispatchFirstRun(creation, query, platform, summary);
      return;
    }
    if (creation.jobType === "query_research_first_run" && creation.status === "delayed") {
      summary.retryScheduled += 1;
      return;
    }
    summary.alreadyReserved += 1;
    return;
  }

  await dispatchFirstRun(creation, query, platform, summary);
}

async function dispatchFirstRun(
  creation: GeoJobCreationResource,
  query: GeoQueryResource,
  platform: GeoPlatformResource,
  summary: GeoQueryFirstRunSummary,
): Promise<void> {
  try {
    const dispatched = await api.geoAnalysis.dispatchJob(creation.id);
    switch (dispatched.status) {
      case "pending":
      case "delayed":
        summary.retryScheduled += 1;
        return;
      case "failed":
      case "cancelled":
        summary.failures.push(
          `${query.queryText}／${platform.displayName}：${dispatched.lastErrorMessage || `首次數據 Job ${dispatched.status}`}`,
        );
        return;
      default:
        summary.dispatched += 1;
    }
  } catch {
    summary.retryScheduled += 1;
  }
}
