import type {
  GeoMarketType,
  GeoProjectQuerySettingsRequest,
  GeoProjectQuerySettingsResource,
} from "../types";
import { ApiError, api } from "./api";

export interface GeoProjectQuerySettingsForm {
  researchProvider: "gemini";
  runProvider: "gemini";
  keywords: string;
  marketType: GeoMarketType;
  maxQueries: number;
  audienceName: string;
  audienceDescription: string;
  intentCategory: string;
  intentDescription: string;
  shouldMentionOwnBrand: boolean;
  shouldMentionCompetitor: boolean;
}

export interface GeoProjectQuerySettingsLoadResult {
  form: GeoProjectQuerySettingsForm;
  warning: string;
}

export function createDefaultQuerySettingsForm(): GeoProjectQuerySettingsForm {
  return {
    researchProvider: "gemini",
    runProvider: "gemini",
    keywords: "",
    marketType: "b2b_procurement",
    maxQueries: 8,
    audienceName: "B2B 採購",
    audienceDescription: "正在評估供應商、產品規格與導入風險的採購或決策者",
    intentCategory: "商業評估",
    intentDescription: "比較供應商、產品方案或導入條件",
    shouldMentionOwnBrand: true,
    shouldMentionCompetitor: true,
  };
}

export async function loadProjectQuerySettings(
  projectId: string,
): Promise<GeoProjectQuerySettingsLoadResult> {
  try {
    return {
      form: querySettingsResourceToForm(await api.geoAnalysis.querySettings(projectId)),
      warning: "",
    };
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) {
      return { form: createDefaultQuerySettingsForm(), warning: "" };
    }
    return {
      form: createDefaultQuerySettingsForm(),
      warning: error instanceof Error
        ? `Query Settings 載入失敗，已使用預設值：${error.message}`
        : "Query Settings 載入失敗，已使用預設值。",
    };
  }
}

export function querySettingsResourceToForm(
  settings: GeoProjectQuerySettingsResource,
): GeoProjectQuerySettingsForm {
  return {
    researchProvider: settings.researchProvider,
    runProvider: settings.runProvider,
    keywords: settings.keywords.join("\n"),
    marketType: settings.marketType,
    maxQueries: settings.maxQueries,
    audienceName: settings.audience.name,
    audienceDescription: settings.audience.description,
    intentCategory: settings.intent.category,
    intentDescription: settings.intent.description,
    shouldMentionOwnBrand: settings.shouldMentionOwnBrand,
    shouldMentionCompetitor: settings.shouldMentionCompetitor,
  };
}

export function querySettingsFormToRequest(
  form: GeoProjectQuerySettingsForm,
): GeoProjectQuerySettingsRequest {
  return {
    researchProvider: form.researchProvider,
    runProvider: form.runProvider,
    keywords: normalizeQuerySettingsKeywords(form.keywords),
    marketType: form.marketType,
    maxQueries: Number(form.maxQueries),
    audience: {
      name: form.audienceName.trim(),
      description: form.audienceDescription.trim(),
    },
    intent: {
      category: form.intentCategory.trim(),
      description: form.intentDescription.trim(),
    },
    shouldMentionOwnBrand: form.shouldMentionOwnBrand,
    shouldMentionCompetitor: form.shouldMentionCompetitor,
  };
}

export function normalizeQuerySettingsKeywords(value: string): string[] {
  const normalized: string[] = [];
  const seen = new Set<string>();
  for (const rawValue of value.split(/\r?\n|[,，]/)) {
    const keyword = rawValue.trim();
    const key = keyword.toLocaleLowerCase();
    if (!keyword || seen.has(key)) continue;
    seen.add(key);
    normalized.push(keyword);
  }
  return normalized;
}

export function querySettingsKeywordTagsToText(tags: readonly string[]): string {
  return normalizeQuerySettingsKeywords(tags.join("\n")).join("\n");
}

export function validateQuerySettingsForm(
  form: GeoProjectQuerySettingsForm,
): Record<string, string> {
  const errors: Record<string, string> = {};
  const keywords = normalizeQuerySettingsKeywords(form.keywords);
  if (keywords.length > 10) errors.keywords = "Keywords 最多 10 筆";
  else if (keywords.some((keyword) => keyword.length > 200)) {
    errors.keywords = "每筆 Keyword 最多 200 字";
  }
  if (!Number.isInteger(Number(form.maxQueries)) || form.maxQueries < 1 || form.maxQueries > 40) {
    errors.maxQueries = "Max Queries 必須是 1–40 的整數";
  }
  validateText(errors, "audienceName", form.audienceName, 200, "Audience");
  validateText(
    errors,
    "audienceDescription",
    form.audienceDescription,
    2000,
    "Audience Description",
  );
  validateText(errors, "intentCategory", form.intentCategory, 100, "Intent 分類");
  validateText(errors, "intentDescription", form.intentDescription, 2000, "Intent 描述");
  return errors;
}

export function validateQueryResearchForm(
  form: GeoProjectQuerySettingsForm,
  topics: ReadonlyArray<{ name: string }>,
): Record<string, string> {
  const errors = validateQuerySettingsForm(form);
  if (!normalizeQuerySettingsKeywords(form.keywords).length) {
    errors.keywords = "請至少輸入一個 Keyword。";
  }
  if (!topics.some((topic) => topic.name.trim())) {
    errors.topics = "請至少輸入一個 Topic。";
  }
  return errors;
}

function validateText(
  errors: Record<string, string>,
  field: string,
  value: string,
  maxLength: number,
  label: string,
): void {
  const normalized = value.trim();
  if (!normalized) errors[field] = `請輸入 ${label}`;
  else if (normalized.length > maxLength) errors[field] = `${label} 最多 ${maxLength} 字`;
}
