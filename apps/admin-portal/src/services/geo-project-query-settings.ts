import type {
  GeoMarketType,
  GeoProjectQuerySettingsRequest,
  GeoProjectQuerySettingsResource,
} from "../types";
import { ApiError, api } from "./api";

export const MAX_GEO_TOPICS = 8;
export const MAX_GEO_KEYWORDS = 10;

export const GEO_QUERY_INTENT_OPTIONS = [
  {
    category: "navigational",
    label: "導航",
    defaultDescription: "尋找特定品牌的官網、地址或官方頁面",
  },
  {
    category: "informational",
    label: "資訊",
    defaultDescription: "查詢知識、定義、教學或特定問題的解答",
  },
  {
    category: "commercial_investigation",
    label: "商業",
    defaultDescription: "比較供應商、產品方案、評價或購買條件",
  },
  {
    category: "transactional",
    label: "交易",
    defaultDescription: "尋找購買、預約、詢價或其他可採取行動的方式",
  },
] as const;

export interface GeoProjectQueryIntentForm {
  category: string;
  label: string;
  description: string;
  selected: boolean;
}

export interface GeoProjectQuerySettingsForm {
  researchProvider: "gemini";
  runProvider: "gemini";
  keywords: string;
  marketType: GeoMarketType;
  maxQueries: number;
  audienceName: string;
  audienceDescription: string;
  intents: GeoProjectQueryIntentForm[];
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
    intents: createIntentForm(),
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
    intents: createIntentForm(settings.intents),
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
    intents: selectedQueryIntents(form),
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
  if (keywords.length > MAX_GEO_KEYWORDS) {
    errors.keywords = `Keywords 最多 ${MAX_GEO_KEYWORDS} 筆`;
  } else if (keywords.some((keyword) => keyword.length > 200)) {
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
  const intents = selectedQueryIntents(form);
  if (!intents.length) {
    errors.intents = "請至少選擇一個 Intent";
  } else if (intents.some((intent) => !intent.description)) {
    errors.intents = "請填寫所有已選 Intent 的描述";
  } else if (intents.some((intent) => intent.description.length > 2000)) {
    errors.intents = "每個 Intent 描述最多 2000 字";
  } else if (Number(form.maxQueries) < intents.length) {
    errors.maxQueries = `Max Queries 不得少於已選 Intent 數量（${intents.length}）`;
  }
  return errors;
}

export function selectedQueryIntents(
  form: GeoProjectQuerySettingsForm,
): GeoProjectQuerySettingsRequest["intents"] {
  return form.intents
    .filter((intent) => intent.selected)
    .map((intent) => ({
      category: intent.category,
      description: intent.description.trim(),
    }));
}

export function queryIntentLabel(category: string | null): string {
  if (!category) return "未分類";
  const normalized = normalizeIntentCategory(category);
  return GEO_QUERY_INTENT_OPTIONS.find(
    (option) => option.category === normalized,
  )?.label ?? "未分類";
}

function createIntentForm(
  savedIntents: GeoProjectQuerySettingsRequest["intents"] = [],
): GeoProjectQueryIntentForm[] {
  const savedByCategory = new Map(
    savedIntents.map((intent) => [normalizeIntentCategory(intent.category), intent]),
  );
  return GEO_QUERY_INTENT_OPTIONS.map((option) => {
    const saved = savedByCategory.get(option.category);
    return {
      category: option.category,
      label: option.label,
      description: saved?.description ?? option.defaultDescription,
      selected: saved ? true : option.category === "commercial_investigation" && !savedIntents.length,
    };
  });
}

function normalizeIntentCategory(category: string): string {
  const aliases: Record<string, string> = {
    導航: "navigational",
    導航型: "navigational",
    資訊: "informational",
    資訊型: "informational",
    商業: "commercial_investigation",
    商業評估: "commercial_investigation",
    commercial: "commercial_investigation",
    交易: "transactional",
    交易型: "transactional",
  };
  return aliases[category.trim()] ?? category.trim();
}

export function validateQueryResearchForm(
  form: GeoProjectQuerySettingsForm,
  topics: ReadonlyArray<{ name: string }>,
): Record<string, string> {
  const errors = validateQuerySettingsForm(form);
  if (!normalizeQuerySettingsKeywords(form.keywords).length) {
    errors.keywords = "請至少輸入一個 Keyword。";
  }
  if (topics.length > MAX_GEO_TOPICS) {
    errors.topics = `Topics 最多 ${MAX_GEO_TOPICS} 筆。`;
  } else if (!topics.some((topic) => topic.name.trim())) {
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
