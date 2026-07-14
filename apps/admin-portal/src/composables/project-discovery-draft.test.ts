import { describe, expect, it } from "vitest";
import {
  applyProjectDiscoveryDraft,
  createProjectIdentityDraft,
  createProjectSuggestionsDraft,
  isProjectIdentityDraftConfirmable,
} from "./project-discovery-draft";

const identityResult = {
  sourceUrl: "https://www.kaiser.com.tw/",
  retrievedUrl: "https://www.kaiser.com.tw/",
  projectName: "港香蘭藥廠股份有限公司",
  projectDescription: "位於台灣的中藥製藥公司。",
  projectType: "company" as const,
  coreOfferings: ["科學中藥"],
};

const suggestionsResult = {
  competitors: ["順天堂藥廠", "勝昌製藥"],
  topics: [
    {
      name: "科學中藥",
      description: "聚焦製程、品質與產品使用情境。",
    },
  ],
  keywords: ["科學中藥", "中藥濃縮粉"],
  references: [{ url: "https://example.com/source", title: "市場來源" }],
};

describe("project discovery draft", () => {
  it("creates independently editable identity and suggestion drafts", () => {
    const identity = createProjectIdentityDraft(identityResult);
    const suggestions = createProjectSuggestionsDraft(suggestionsResult);

    identity.projectName = "港香蘭";
    identity.coreOfferings[0] = "編輯後服務";
    suggestions.competitors[0] = "編輯後競品";
    suggestions.topics[0].name = "編輯後 Topic";

    expect(identityResult.projectName).toBe("港香蘭藥廠股份有限公司");
    expect(identityResult.coreOfferings[0]).toBe("科學中藥");
    expect(suggestionsResult.competitors[0]).toBe("順天堂藥廠");
    expect(suggestionsResult.topics[0].name).toBe("科學中藥");
  });

  it("returns a complete replacement for the Query Research fields", () => {
    const identity = createProjectIdentityDraft(identityResult);
    const suggestions = createProjectSuggestionsDraft(suggestionsResult);
    identity.projectName = " 港香蘭 ";
    suggestions.competitors.push(" ");
    suggestions.keywords.push(" ");
    suggestions.topics.push({ name: "缺少描述", description: " " });

    const replacement = applyProjectDiscoveryDraft(identity, suggestions);

    expect(replacement).toEqual({
      brandName: "港香蘭",
      competitorBrands: "順天堂藥廠\n勝昌製藥",
      topics: [
        {
          name: "科學中藥",
          description: "聚焦製程、品質與產品使用情境。",
        },
      ],
      keywords: "科學中藥\n中藥濃縮粉",
    });
  });

  it("requires name, description, and a core offering before Stage 2", () => {
    const identity = createProjectIdentityDraft(identityResult);

    expect(isProjectIdentityDraftConfirmable(identity)).toBe(true);

    identity.projectDescription = " ";
    expect(isProjectIdentityDraftConfirmable(identity)).toBe(false);

    identity.projectDescription = "可用描述";
    identity.coreOfferings = [" "];
    expect(isProjectIdentityDraftConfirmable(identity)).toBe(false);
  });
});
