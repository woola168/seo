import { afterEach, describe, expect, it, vi } from "vitest";

import { createPortalNotifications } from "./portal-notifications";

describe("portal notifications", () => {
  afterEach(() => vi.useRealTimers());

  it("replaces the visible toast and dismisses it after three seconds", () => {
    vi.useFakeTimers();
    const notifications = createPortalNotifications();

    notifications.notify("first");
    notifications.notify("saved", "success");

    expect(notifications.toast.value).toMatchObject({
      message: "saved",
      tone: "success",
    });

    vi.advanceTimersByTime(3000);
    expect(notifications.toast.value).toBeNull();
  });
});
