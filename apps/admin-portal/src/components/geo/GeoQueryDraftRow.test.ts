// @vitest-environment jsdom

import { mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import type { GeoQueryDraftResource } from "../../types";
import GeoQueryDraftRow from "./GeoQueryDraftRow.vue";

function draft(keywords: string[] = []): GeoQueryDraftResource {
  return {
    id: "draft-1",
    generationRunId: "run-1",
    projectId: "project-1",
    topicId: null,
    topicName: "產品",
    queryText: "睡眠保健食品推薦",
    keywords,
    region: "TW",
    language: "zh-TW",
    marketType: "b2c",
    intent: "commercial_investigation",
    isBranded: false,
    status: "draft",
    selectionStatus: null,
    acceptedQueryId: null,
    metadata: {},
    createdAt: "2026-08-01T00:00:00Z",
    updatedAt: "2026-08-01T00:00:00Z",
  };
}

function mountRow(candidate: GeoQueryDraftResource) {
  return mount(GeoQueryDraftRow, {
    props: {
      draft: candidate,
      selected: false,
      updating: false,
      intentLabel: "商業",
    },
  });
}

describe("GeoQueryDraftRow", () => {
  it("displays every candidate keyword as a tag", () => {
    const wrapper = mountRow(draft(["睡眠", "保健食品"]));

    expect(
      wrapper.findAll(".geo-result-keyword-list .badge").map((tag) => tag.text()),
    ).toEqual(["睡眠", "保健食品"]);
  });

  it("displays a dash when the candidate has no keywords", () => {
    const wrapper = mountRow(draft());

    expect(wrapper.findAll(".geo-result-keyword-list .badge")).toHaveLength(0);
    expect(wrapper.get(".geo-result-keyword-list").text()).toBe("—");
  });

  it("emits the candidate when the row is clicked", async () => {
    const candidate = draft(["睡眠"]);
    const wrapper = mountRow(candidate);

    await wrapper.get("button").trigger("click");

    expect(wrapper.emitted("toggle")).toEqual([[candidate]]);
  });
});
