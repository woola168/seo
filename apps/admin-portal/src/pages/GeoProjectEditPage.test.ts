// @vitest-environment jsdom

import { flushPromises, mount } from "@vue/test-utils";
import { beforeEach, describe, expect, it, vi } from "vitest";

const mocks = vi.hoisted(() => ({
  route: {
    params: {} as Record<string, string>,
    query: {} as Record<string, string>,
    meta: { geoProjectArea: "standard" },
  },
  routerPush: vi.fn(),
  routerReplace: vi.fn(),
  notify: vi.fn(),
  customers: vi.fn(),
  loadProfile: vi.fn(),
  createProfile: vi.fn(),
  updateProfile: vi.fn(),
}));

vi.mock("vue-router", () => ({
  useRoute: () => mocks.route,
  useRouter: () => ({ push: mocks.routerPush, replace: mocks.routerReplace }),
}));

vi.mock("../composables/portal-context", () => ({
  usePortalSession: () => ({
    capabilities: {
      value: { permissions: ["geo.projects.update", "geo.queries.manage"] },
    },
  }),
  usePortalNotifications: () => ({ notify: mocks.notify }),
}));

vi.mock("../services/api", () => ({
  api: {
    customers: mocks.customers,
  },
}));

vi.mock("../services/geo-project-profile", () => {
  class GeoProjectProfileSaveError extends Error {
    constructor(
      message: string,
      readonly project: { id: string },
    ) {
      super(message);
    }
  }

  return {
    GeoProjectProfileSaveError,
    loadGeoProjectProfile: mocks.loadProfile,
    createGeoProjectWithQuerySettings: mocks.createProfile,
    updateGeoProjectProfile: mocks.updateProfile,
    normalizeValues: (values: string[]) => Array.from(
      new Set(values.map((value) => value.trim()).filter(Boolean)),
    ),
  };
});

import GeoProjectEditPage from "./GeoProjectEditPage.vue";

beforeEach(() => {
  vi.clearAllMocks();
  mocks.route.params = { projectId: "project-1" };
  mocks.route.query = {};
  mocks.customers.mockResolvedValue({
    items: [{ id: "customer-1", name: "客戶一" }],
    total: 1,
  });
  mocks.loadProfile.mockResolvedValue(profile());
  mocks.updateProfile.mockResolvedValue({ id: "project-1" });
});

describe("GeoProjectEditPage brand identity validation", () => {
  it("blocks a modal competitor name matching the current own-brand canonical name", async () => {
    const wrapper = await mountPage();

    await buttonWithText(wrapper, "新增").trigger("click");
    await wrapper.get('input[placeholder="請輸入競品名稱"]').setValue("TRACKED BRAND");
    await buttonWithText(wrapper, "儲存", ".geo-competitor-dialog").trigger("click");

    expect(wrapper.get(".geo-competitor-dialog").text()).toContain(
      "競品名稱不可與自有品牌名稱或別名相同",
    );
    expect(mocks.updateProfile).not.toHaveBeenCalled();
  });

  it("rechecks existing competitors before saving and does not call the API", async () => {
    mocks.loadProfile.mockResolvedValue(profile({ competitorName: "Tracked Brand" }));
    const wrapper = await mountPage();

    await buttonWithText(wrapper, "儲存").trigger("click");

    expect(wrapper.text()).toContain(
      "競品名稱或別名不可與自有品牌名稱或別名相同：Tracked Brand",
    );
    expect(mocks.updateProfile).not.toHaveBeenCalled();
  });

  it("clears a stale conflict error when the conflicting competitor is removed", async () => {
    mocks.loadProfile.mockResolvedValue(profile({ competitorName: "Tracked Brand" }));
    const wrapper = await mountPage();
    await buttonWithText(wrapper, "儲存").trigger("click");

    await wrapper.get('button[title="刪除"]').trigger("click");

    expect(wrapper.text()).not.toContain(
      "競品名稱或別名不可與自有品牌名稱或別名相同",
    );
  });

  it("blocks a conflicting competitor tag in the create flow", async () => {
    mocks.route.params = {};
    const wrapper = await mountPage();
    await wrapper.get('input[placeholder="請輸入名稱"]').setValue("Acme");
    await wrapper.get('input[placeholder="請輸入網址/網域"]').setValue("https://acme.example");
    const competitorInput = wrapper.get('input[placeholder="請輸入競品"]');
    await competitorInput.setValue("ＡＣＭＥ");
    await competitorInput.trigger("keydown", { key: "Enter" });

    await buttonWithText(wrapper, "下一步").trigger("click");

    expect(wrapper.text()).toContain(
      "競品名稱或別名不可與自有品牌名稱或別名相同：ＡＣＭＥ",
    );
    expect(mocks.createProfile).not.toHaveBeenCalled();
  });
});

async function mountPage() {
  const wrapper = mount(GeoProjectEditPage, {
    global: {
      stubs: {
        AppIcon: true,
        GeoQueryResearchPage: true,
        Teleport: true,
      },
    },
  });
  await flushPromises();
  return wrapper;
}

function buttonWithText(
  wrapper: ReturnType<typeof mount>,
  text: string,
  container?: string,
) {
  const root = container ? wrapper.get(container) : wrapper;
  const button = root.findAll("button").find((candidate) => candidate.text().trim() === text);
  if (!button) throw new Error(`Button not found: ${text}`);
  return button;
}

function profile(options: { competitorName?: string } = {}) {
  const competitors = options.competitorName
    ? [
        {
          clientId: "competitor-1",
          entity: { id: "competitor-1" },
          name: options.competitorName,
          websiteUrl: "",
          aliases: [],
        },
      ]
    : [];
  return {
    project: {
      id: "project-1",
      customerId: "customer-1",
      name: "Display Project",
      defaultRegion: "TW",
      defaultLanguage: "zh-TW",
      status: "active",
      dailyRunBudget: 200,
    },
    customerName: "客戶一",
    ownBrand: {
      entity: { id: "own-brand-1" },
      name: "Tracked Brand",
      websiteUrl: "https://brand.example",
      aliases: [{ alias: "Brand Alias" }],
    },
    competitors,
    topics: [],
    queries: [],
  };
}
