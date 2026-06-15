import { describe, expect, it } from "vitest";
import { createMemoryHistory } from "vue-router";

import {
  createPortalRouter,
  getLoginRedirect,
  getRoutePage,
} from "./routes";

describe("portal router", () => {
  it("redirects protected pages to login and preserves the destination", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/permissions");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("login");
    expect(router.currentRoute.value.query.redirect).toBe("/permissions");
  });

  it("redirects authenticated users away from login", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => true);

    await router.push("/login");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("dashboard");
  });

  it("keeps account recovery routes public", async () => {
    const router = createPortalRouter(createMemoryHistory(), () => false);

    await router.push("/reset-password?token=example");
    await router.isReady();

    expect(router.currentRoute.value.name).toBe("reset-password");
    expect(router.currentRoute.value.query.token).toBe("example");
  });
});

describe("route helpers", () => {
  it("maps route metadata to an available portal page", () => {
    expect(getRoutePage("permissions")).toBe("permissions");
    expect(getRoutePage(undefined)).toBe("dashboard");
  });

  it("accepts only local post-login redirects", () => {
    expect(getLoginRedirect("/permissions")).toBe("/permissions");
    expect(getLoginRedirect("https://example.com")).toBe("/dashboard");
    expect(getLoginRedirect("//example.com")).toBe("/dashboard");
  });
});
