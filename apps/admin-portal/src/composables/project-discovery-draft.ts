import type {
  GeoConfirmedProjectIdentity,
  GeoProjectInspectionResult,
  GeoProjectSuggestionsResult,
  GeoTopicInput,
} from "../types";

export interface ProjectIdentityDraft extends GeoConfirmedProjectIdentity {}

export interface ProjectSuggestionsDraft extends GeoProjectSuggestionsResult {}

export interface QueryResearchProjectReplacement {
  brandName: string;
  competitorBrands: string;
  topics: GeoTopicInput[];
  keywords: string;
}

export function createProjectIdentityDraft(
  result: GeoProjectInspectionResult,
): ProjectIdentityDraft {
  return {
    ...result,
    coreOfferings: [...result.coreOfferings],
    targetAudiences: [...result.targetAudiences],
  };
}

export function createProjectSuggestionsDraft(
  result: GeoProjectSuggestionsResult,
): ProjectSuggestionsDraft {
  return {
    competitors: [...result.competitors],
    topics: result.topics.map((topic) => ({ ...topic })),
    keywords: [...result.keywords],
    references: result.references.map((reference) => ({ ...reference })),
  };
}

export function applyProjectDiscoveryDraft(
  identity: ProjectIdentityDraft,
  suggestions: ProjectSuggestionsDraft,
): QueryResearchProjectReplacement {
  return {
    brandName: identity.projectName.trim(),
    competitorBrands: cleanedLines(suggestions.competitors).join("\n"),
    topics: suggestions.topics
      .map((topic) => ({
        name: topic.name.trim(),
        description: topic.description.trim(),
      }))
      .filter((topic) => topic.name && topic.description),
    keywords: cleanedLines(suggestions.keywords).join("\n"),
  };
}

export function isProjectIdentityDraftConfirmable(
  identity: ProjectIdentityDraft,
): boolean {
  return Boolean(
    identity.projectName.trim() &&
      identity.projectDescription.trim() &&
      cleanedLines(identity.coreOfferings).length,
  );
}

function cleanedLines(values: string[]): string[] {
  return values.map((value) => value.trim()).filter(Boolean);
}
