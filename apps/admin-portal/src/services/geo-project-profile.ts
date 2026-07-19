import { api } from "./api";
import type {
  CustomerSummary,
  GeoEntityAliasResource,
  GeoEntityResource,
  GeoProjectRequest,
  GeoProjectQuerySettingsRequest,
  GeoProjectResource,
  GeoQueryResource,
  GeoTopicResource,
} from "../types";

export interface GeoProjectBrand {
  entity: GeoEntityResource | null;
  name: string;
  websiteUrl: string;
  aliases: GeoEntityAliasResource[];
}

export interface GeoProjectCompetitor extends GeoProjectBrand {
  clientId: string;
}

export interface GeoProjectProfile {
  project: GeoProjectResource;
  customerName: string;
  ownBrand: GeoProjectBrand;
  competitors: GeoProjectCompetitor[];
  topics: GeoTopicResource[];
  queries: GeoQueryResource[];
}

export interface GeoProjectProfileInput {
  project: GeoProjectRequest;
  websiteUrl: string;
  aliases: string[];
  competitors: Array<{
    id: string | null;
    name: string;
    websiteUrl: string;
    aliases: string[];
  }>;
  topics: Array<{ name: string; description: string }>;
}

export class GeoProjectProfileSaveError extends Error {
  constructor(
    message: string,
    readonly project: GeoProjectResource,
  ) {
    super(message);
  }
}

export type GeoProjectCreationResult =
  | { project: GeoProjectResource; querySettingsStatus: "saved" }
  | { project: GeoProjectResource; querySettingsStatus: "skipped" }
  | { project: GeoProjectResource; querySettingsStatus: "failed"; querySettingsError: string };

export async function loadGeoProjectProfile(projectId: string): Promise<GeoProjectProfile> {
  const [project, customers, entities, aliases, topics, queries] = await Promise.all([
    api.geoAnalysis.project(projectId),
    api.customers().catch(() => ({ items: [], total: 0 })),
    api.geoAnalysis.entities(projectId),
    api.geoAnalysis.projectAliases(projectId),
    api.geoAnalysis.topics(projectId),
    api.geoAnalysis.queries(projectId),
  ]);
  return buildGeoProjectProfile(
    project,
    customers.items,
    entities.items,
    aliases.items,
    topics.items,
    queries.items,
  );
}

export function buildGeoProjectProfile(
  project: GeoProjectResource,
  customers: CustomerSummary[],
  entities: GeoEntityResource[],
  aliases: GeoEntityAliasResource[],
  topics: GeoTopicResource[],
  queries: GeoQueryResource[],
): GeoProjectProfile {
  const ownEntity = entities.find((entity) => entity.entityType === "own_brand") ?? null;
  const entityAliases = (entity: GeoEntityResource | null) =>
    entity ? aliases.filter((alias) => alias.entityId === entity.id) : [];
  return {
    project,
    customerName:
      customers.find((customer) => customer.id === project.customerId)?.name ??
      (project.customerId ? `Customer ${project.customerId.slice(0, 8)}` : "未綁定 Customer"),
    ownBrand: {
      entity: ownEntity,
      name: ownEntity?.name ?? project.name,
      websiteUrl: ownEntity?.websiteUrl ?? "",
      aliases: entityAliases(ownEntity),
    },
    competitors: entities
      .filter((entity) => entity.entityType === "competitor")
      .map((entity) => ({
        clientId: entity.id,
        entity,
        name: entity.name,
        websiteUrl: entity.websiteUrl ?? "",
        aliases: entityAliases(entity),
      })),
    topics,
    queries,
  };
}

export async function createGeoProjectProfile(input: GeoProjectProfileInput): Promise<GeoProjectResource> {
  const project = await api.geoAnalysis.createProject(input.project);
  try {
    await saveRelatedProfile(project, null, input);
  } catch (error) {
    throw new GeoProjectProfileSaveError(errorMessage(error), project);
  }
  return project;
}

export async function createGeoProjectWithQuerySettings(
  input: GeoProjectProfileInput,
  settings: GeoProjectQuerySettingsRequest,
  canUpdateProject: boolean,
): Promise<GeoProjectCreationResult> {
  const project = await createGeoProjectProfile(input);
  if (!canUpdateProject) {
    return { project, querySettingsStatus: "skipped" };
  }
  try {
    await api.geoAnalysis.updateQuerySettings(project.id, settings);
    return { project, querySettingsStatus: "saved" };
  } catch (error) {
    return {
      project,
      querySettingsStatus: "failed",
      querySettingsError: errorMessage(error),
    };
  }
}

export async function updateGeoProjectProfile(
  current: GeoProjectProfile,
  input: GeoProjectProfileInput,
): Promise<GeoProjectResource> {
  const project = await api.geoAnalysis.updateProject(current.project.id, input.project);
  try {
    await saveRelatedProfile(project, current, input);
  } catch (error) {
    throw new GeoProjectProfileSaveError(errorMessage(error), project);
  }
  return project;
}

async function saveRelatedProfile(
  project: GeoProjectResource,
  current: GeoProjectProfile | null,
  input: GeoProjectProfileInput,
): Promise<void> {
  const ownBrand = current?.ownBrand.entity
    ? await api.geoAnalysis.updateEntity(current.ownBrand.entity.id, {
        entityType: "own_brand",
        name: project.name,
        websiteUrl: valueOrNull(input.websiteUrl),
        description: current.ownBrand.entity.description,
        status: "active",
      })
    : await api.geoAnalysis.createEntity(project.id, {
        entityType: "own_brand",
        name: project.name,
        websiteUrl: valueOrNull(input.websiteUrl),
        description: "GEO Project 主要品牌。",
        status: "active",
      });
  await syncAliases(ownBrand.id, current?.ownBrand.aliases ?? [], input.aliases);

  const currentCompetitors = new Map(
    (current?.competitors ?? []).map((competitor) => [competitor.entity?.id, competitor]),
  );
  const retainedIds = new Set(input.competitors.map((competitor) => competitor.id).filter(Boolean));
  for (const competitor of current?.competitors ?? []) {
    if (competitor.entity && !retainedIds.has(competitor.entity.id)) {
      await api.geoAnalysis.deleteEntity(competitor.entity.id);
    }
  }
  for (const competitor of input.competitors) {
    const existing = competitor.id ? currentCompetitors.get(competitor.id) : undefined;
    const entity = existing?.entity
      ? await api.geoAnalysis.updateEntity(existing.entity.id, {
          entityType: "competitor",
          name: competitor.name,
          websiteUrl: valueOrNull(competitor.websiteUrl),
          description: existing.entity.description,
          status: "active",
        })
      : await api.geoAnalysis.createEntity(project.id, {
          entityType: "competitor",
          name: competitor.name,
          websiteUrl: valueOrNull(competitor.websiteUrl),
          description: "GEO Project 競品。",
          status: "active",
        });
    await syncAliases(entity.id, existing?.aliases ?? [], competitor.aliases);
  }

  if (!current) {
    for (const topic of input.topics) {
      await api.geoAnalysis.createTopic(project.id, {
        name: topic.name,
        description: topic.description,
        status: "active",
      });
    }
  }
}

async function syncAliases(
  entityId: string,
  current: GeoEntityAliasResource[],
  values: string[],
): Promise<void> {
  const wanted = new Set(normalizeValues(values));
  for (const alias of current) {
    if (!wanted.has(alias.alias)) await api.geoAnalysis.deleteAlias(alias.id);
  }
  const currentValues = new Set(current.map((alias) => alias.alias));
  for (const alias of wanted) {
    if (!currentValues.has(alias)) {
      await api.geoAnalysis.createAlias(entityId, { alias, matchType: "exact" });
    }
  }
}

export function normalizeValues(values: string[]): string[] {
  return Array.from(new Set(values.map((value) => value.trim()).filter(Boolean)));
}

function valueOrNull(value: string): string | null {
  return value.trim() || null;
}

function errorMessage(error: unknown): string {
  return error instanceof Error ? error.message : "Project 關聯資料保存失敗。";
}
