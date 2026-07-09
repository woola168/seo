import { describe, expect, it } from "vitest";

import {
  validateAcceptDraftStep,
  validateDispatchStep,
  validateGenerationStep,
  validateProjectStep,
  validateResearchStep,
} from "./geo-flow-validation";

describe("geo flow validation", () => {
  it("requires either an existing project or a new project name", () => {
    expect(validateProjectStep({})).toEqual([
      { field: "project", message: "請選擇既有 project 或輸入新 project 名稱" },
      { field: "customerId", message: "請選擇 customer" },
    ]);
  });

  it("requires a customer for the flow-check project binding", () => {
    expect(validateProjectStep({ projectName: "GEO Flow Check" })).toEqual([
      { field: "customerId", message: "請選擇 customer" },
    ]);
  });

  it("accepts a project with a customer binding", () => {
    expect(
      validateProjectStep({
        projectName: "GEO Flow Check",
        customerId: "customer-1",
      }),
    ).toEqual([]);
  });

  it("reports all required query planning fields before API calls", () => {
    expect(validateResearchStep({ projectId: "project-1" })).toEqual([
      { field: "brandName", message: "請輸入品牌名稱" },
      { field: "keywords", message: "請至少輸入一個 keyword" },
      { field: "topics", message: "請至少輸入一個 topic" },
      { field: "intentDescription", message: "請輸入 Intent 描述" },
      { field: "audienceName", message: "請輸入受眾名稱" },
      { field: "audienceDescription", message: "請輸入受眾描述" },
    ]);
  });

  it("does not require seoTaskId before query generation", () => {
    const errors = validateGenerationStep({
      projectId: "project-1",
      brandName: "Acme",
      keywords: ["erp"],
      topics: [{ name: "ERP 導入" }],
      intentDescription: "比較供應商",
      audienceName: "採購",
      audienceDescription: "B2B 採購決策者",
    });

    expect(errors).toEqual([]);
  });

  it("requires a selected draft before accept", () => {
    expect(validateAcceptDraftStep({})).toEqual([
      { field: "draft", message: "請先選擇一筆 query draft" },
    ]);
  });

  it("requires dispatch prerequisites without requiring a pre-created job", () => {
    expect(validateDispatchStep({ projectId: "project-1" })).toEqual([
      { field: "acceptedQuery", message: "請先選擇至少一筆正式 query" },
      { field: "platform", message: "請選擇 run provider" },
    ]);
  });
});
