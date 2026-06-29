export type GeoFlowValidationInput = {
  projectId?: string;
  projectName?: string;
  brandName?: string;
  keywords?: Array<string>;
  topics?: Array<{ name: string; description?: string }>;
  audienceName?: string;
  audienceDescription?: string;
  seoTaskId?: string | null;
  draftId?: string | null;
  acceptedQueryId?: string | null;
  platformId?: string | null;
  jobId?: string | null;
};

export type GeoFlowValidationError = {
  field: string;
  message: string;
};

export function validateProjectStep(
  input: GeoFlowValidationInput,
): GeoFlowValidationError[] {
  const errors: GeoFlowValidationError[] = [];
  if (!hasValue(input.projectId) && !hasValue(input.projectName)) {
    errors.push({ field: "project", message: "請選擇既有 project 或輸入新 project 名稱" });
  }
  return errors;
}

export function validateResearchStep(
  input: GeoFlowValidationInput,
): GeoFlowValidationError[] {
  const errors: GeoFlowValidationError[] = [];
  if (!hasValue(input.projectId)) {
    errors.push({ field: "project", message: "請先選擇或建立 GEO project" });
  }
  if (!hasValue(input.brandName)) {
    errors.push({ field: "brandName", message: "請輸入品牌名稱" });
  }
  if (!input.keywords?.length) {
    errors.push({ field: "keywords", message: "請至少輸入一個 keyword" });
  }
  if (!input.topics?.some((topic) => hasValue(topic.name))) {
    errors.push({ field: "topics", message: "請至少輸入一個 topic" });
  }
  if (!hasValue(input.audienceName)) {
    errors.push({ field: "audienceName", message: "請輸入受眾名稱" });
  }
  if (!hasValue(input.audienceDescription)) {
    errors.push({ field: "audienceDescription", message: "請輸入受眾描述" });
  }
  return errors;
}

export function validateGenerationStep(
  input: GeoFlowValidationInput,
): GeoFlowValidationError[] {
  const errors = validateResearchStep(input);
  if (!hasValue(input.seoTaskId)) {
    errors.push({ field: "seoTaskId", message: "Query generation 需要 seoTaskId" });
  }
  return errors;
}

export function validateAcceptDraftStep(
  input: GeoFlowValidationInput,
): GeoFlowValidationError[] {
  if (!hasValue(input.draftId)) {
    return [{ field: "draft", message: "請先選擇一筆 query draft" }];
  }
  return [];
}

export function validateDispatchStep(
  input: GeoFlowValidationInput,
): GeoFlowValidationError[] {
  const errors: GeoFlowValidationError[] = [];
  if (!hasValue(input.projectId)) {
    errors.push({ field: "project", message: "請先選擇或建立 GEO project" });
  }
  if (!hasValue(input.seoTaskId)) {
    errors.push({ field: "seoTaskId", message: "Dispatch 需要 seoTaskId" });
  }
  if (!hasValue(input.acceptedQueryId)) {
    errors.push({ field: "acceptedQuery", message: "請先選擇至少一筆正式 query" });
  }
  if (!hasValue(input.platformId)) {
    errors.push({ field: "platform", message: "請選擇 run provider" });
  }
  return errors;
}

export function toFieldErrorMap(
  errors: GeoFlowValidationError[],
): Record<string, string> {
  return Object.fromEntries(errors.map((error) => [error.field, error.message]));
}

function hasValue(value: string | null | undefined): boolean {
  return Boolean(value?.trim());
}
