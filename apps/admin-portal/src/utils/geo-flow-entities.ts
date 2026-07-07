import type { GeoEntityRequest, GeoEntityResource } from "../types";

export interface GeoFlowEntityInput {
  brandName: string;
  brandWebsiteUrl: string;
  competitorBrands: string;
  existingEntities: GeoEntityResource[];
}

export interface GeoFlowEntityUpsert {
  existing: GeoEntityResource | null;
  request: GeoEntityRequest;
}

export interface GeoFlowEntityRequests {
  ownBrand: GeoFlowEntityUpsert | null;
  competitors: GeoFlowEntityUpsert[];
}

interface CompetitorInput {
  name: string;
  websiteUrl: string | null;
}

export function parseCompetitorEntityInputs(value: string): CompetitorInput[] {
  const inputs: CompetitorInput[] = [];
  for (const rawLine of value.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line) continue;
    const parts = line.includes("|") ? [line] : line.split(",");
    for (const part of parts) {
      const [namePart, urlPart] = part.split("|");
      const name = namePart?.trim() ?? "";
      if (!name) continue;
      inputs.push({
        name,
        websiteUrl: normalizeUrl(urlPart),
      });
    }
  }
  return dedupeCompetitors(inputs);
}

export function buildFlowEntityRequests(input: GeoFlowEntityInput): GeoFlowEntityRequests {
  const ownBrandName = input.brandName.trim();
  const existingOwnBrand = ownBrandName
    ? findExistingEntity(input.existingEntities, "own_brand", ownBrandName)
    : null;
  const ownBrand: GeoFlowEntityUpsert | null = ownBrandName
    ? {
        existing: existingOwnBrand,
        request: {
          entityType: "own_brand",
          name: ownBrandName,
          websiteUrl: normalizeUrl(input.brandWebsiteUrl) ?? existingOwnBrand?.websiteUrl ?? null,
          description:
            existingOwnBrand?.description ||
            "Created by GEO Flow Check for semantic analysis context.",
          status: "active",
        },
      }
    : null;

  return {
    ownBrand,
    competitors: parseCompetitorEntityInputs(input.competitorBrands).map<GeoFlowEntityUpsert>((competitor) => {
      const existingCompetitor = findExistingEntity(
        input.existingEntities,
        "competitor",
        competitor.name,
      );
      return {
        existing: existingCompetitor,
        request: {
          entityType: "competitor",
          name: competitor.name,
          websiteUrl: competitor.websiteUrl ?? existingCompetitor?.websiteUrl ?? null,
          description:
            existingCompetitor?.description || "Created by GEO Flow Check competitor context.",
          status: "active",
        },
      };
    }),
  };
}

function findExistingEntity(
  entities: GeoEntityResource[],
  entityType: GeoEntityRequest["entityType"],
  name: string,
): GeoEntityResource | null {
  const normalizedName = normalizeName(name);
  return (
    entities.find(
      (entity) =>
        entity.entityType === entityType &&
        normalizeName(entity.name) === normalizedName,
    ) ?? null
  );
}

function normalizeName(value: string): string {
  return value.trim().toLocaleLowerCase();
}

function normalizeUrl(value: string | undefined): string | null {
  const normalized = value?.trim() ?? "";
  return normalized ? normalized : null;
}

function dedupeCompetitors(inputs: CompetitorInput[]): CompetitorInput[] {
  const seen = new Set<string>();
  const results: CompetitorInput[] = [];
  for (const input of inputs) {
    const key = normalizeName(input.name);
    if (seen.has(key)) continue;
    seen.add(key);
    results.push(input);
  }
  return results;
}
