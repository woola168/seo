import { getCurrentScope, onScopeDispose, ref, type Ref } from "vue";

export type LatestRequestResult<T> =
  | { status: "completed"; value: T }
  | { status: "failed"; error: unknown }
  | { status: "aborted" }
  | { status: "ignored" };

export interface LatestRequest {
  loading: Ref<boolean>;
  run<T>(
    key: string,
    request: (signal: AbortSignal) => Promise<T>,
  ): Promise<LatestRequestResult<T>>;
  abort(): void;
}

export function useLatestRequest(): LatestRequest {
  const loading = ref(false);
  let activeKey: string | null = null;
  let activeController: AbortController | null = null;
  let requestId = 0;

  async function run<T>(
    key: string,
    request: (signal: AbortSignal) => Promise<T>,
  ): Promise<LatestRequestResult<T>> {
    if (activeKey === key && activeController !== null) {
      return { status: "ignored" };
    }

    activeController?.abort();
    const controller = new AbortController();
    const currentRequestId = ++requestId;
    activeKey = key;
    activeController = controller;
    loading.value = true;

    try {
      const value = await request(controller.signal);
      if (currentRequestId !== requestId) return { status: "aborted" };
      return { status: "completed", value };
    } catch (error) {
      if (
        controller.signal.aborted ||
        (typeof error === "object" && error !== null && "name" in error && error.name === "AbortError")
      ) {
        return { status: "aborted" };
      }
      if (currentRequestId !== requestId) return { status: "aborted" };
      return { status: "failed", error };
    } finally {
      if (currentRequestId === requestId) {
        activeKey = null;
        activeController = null;
        loading.value = false;
      }
    }
  }

  function abort(): void {
    requestId += 1;
    activeController?.abort();
    activeKey = null;
    activeController = null;
    loading.value = false;
  }

  if (getCurrentScope()) onScopeDispose(abort);

  return { loading, run, abort };
}
