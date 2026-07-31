import { effectScope } from "vue";
import { describe, expect, it, vi } from "vitest";

import { useLatestRequest } from "./latest-request";

describe("useLatestRequest", () => {
  it("deduplicates an in-flight request with the same key", async () => {
    let resolveRequest!: (value: string) => void;
    const request = vi.fn(
      () => new Promise<string>((resolve) => {
        resolveRequest = resolve;
      }),
    );
    const runner = useLatestRequest();

    const first = runner.run("same", request);
    const duplicate = await runner.run("same", request);

    expect(request).toHaveBeenCalledTimes(1);
    expect(duplicate).toEqual({ status: "ignored" });
    expect(runner.loading.value).toBe(true);

    resolveRequest("完成");
    await expect(first).resolves.toEqual({ status: "completed", value: "完成" });
    expect(runner.loading.value).toBe(false);
  });

  it("aborts an older request when a new key starts", async () => {
    const runner = useLatestRequest();
    const first = runner.run(
      "old",
      (signal) => new Promise<string>((_resolve, reject) => {
        signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      }),
    );

    const second = runner.run("new", async () => "最新結果");

    await expect(first).resolves.toEqual({ status: "aborted" });
    await expect(second).resolves.toEqual({ status: "completed", value: "最新結果" });
    expect(runner.loading.value).toBe(false);
  });

  it("returns the current request failure and releases loading", async () => {
    const runner = useLatestRequest();
    const error = new Error("載入失敗");

    await expect(
      runner.run("failed", async () => {
        throw error;
      }),
    ).resolves.toEqual({ status: "failed", error });
    expect(runner.loading.value).toBe(false);
  });

  it("aborts the active request when its Vue scope is disposed", async () => {
    const scope = effectScope();
    const runner = scope.run(() => useLatestRequest());
    if (!runner) throw new Error("無法建立 request coordinator");
    const pending = runner.run(
      "active",
      (signal) => new Promise<string>((_resolve, reject) => {
        signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      }),
    );

    scope.stop();

    await expect(pending).resolves.toEqual({ status: "aborted" });
    expect(runner.loading.value).toBe(false);
  });
});
