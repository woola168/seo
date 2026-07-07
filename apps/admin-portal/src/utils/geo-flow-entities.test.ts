import { describe, expect, it } from "vitest";

import type { GeoEntityResource } from "../types";
import {
  buildFlowEntityRequests,
  parseCompetitorEntityInputs,
} from "./geo-flow-entities";

describe("geo flow entity helpers", () => {
  it("builds an own_brand entity from the brand name", () => {
    const requests = buildFlowEntityRequests({
      brandName: "Kinsan Hotel",
      brandWebsiteUrl: "https://kinsan.example",
      competitorBrands: "",
      existingEntities: [],
    });

    expect(requests.ownBrand?.existing).toBeNull();
    expect(requests.ownBrand?.request).toMatchObject({
      entityType: "own_brand",
      name: "Kinsan Hotel",
      websiteUrl: "https://kinsan.example",
      status: "active",
    });
  });

  it("parses competitor lines with optional website URLs", () => {
    expect(
      parseCompetitorEntityInputs(
        "Alpha Hotel | https://alpha.example\nBeta Hotel\nGamma, Delta",
      ),
    ).toEqual([
      { name: "Alpha Hotel", websiteUrl: "https://alpha.example" },
      { name: "Beta Hotel", websiteUrl: null },
      { name: "Gamma", websiteUrl: null },
      { name: "Delta", websiteUrl: null },
    ]);
  });

  it("reuses existing entities by type and case-insensitive name", () => {
    const existing = [
      entity("entity-own", "own_brand", "kinsan hotel"),
      entity("entity-competitor", "competitor", "Alpha Hotel"),
    ];

    const requests = buildFlowEntityRequests({
      brandName: "Kinsan Hotel",
      brandWebsiteUrl: "",
      competitorBrands: "alpha hotel | https://alpha.example",
      existingEntities: existing,
    });

    expect(requests.ownBrand?.existing?.id).toBe("entity-own");
    expect(requests.competitors[0]?.existing?.id).toBe("entity-competitor");
  });

  it("preserves existing entity details when the flow input leaves them empty", () => {
    const existing = [
      {
        ...entity("entity-own", "own_brand", "Kinsan Hotel"),
        websiteUrl: "https://kinsan.example",
        description: "Existing brand description",
      },
    ];

    const requests = buildFlowEntityRequests({
      brandName: "Kinsan Hotel",
      brandWebsiteUrl: "",
      competitorBrands: "",
      existingEntities: existing,
    });

    expect(requests.ownBrand?.request.websiteUrl).toBe("https://kinsan.example");
    expect(requests.ownBrand?.request.description).toBe("Existing brand description");
  });
});

function entity(
  id: string,
  entityType: GeoEntityResource["entityType"],
  name: string,
): GeoEntityResource {
  return {
    id,
    projectId: "project-1",
    entityType,
    name,
    websiteUrl: null,
    description: "",
    status: "active",
    createdAt: "2026-01-01T00:00:00Z",
    updatedAt: "2026-01-01T00:00:00Z",
  };
}
