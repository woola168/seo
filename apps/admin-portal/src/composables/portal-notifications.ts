import { ref } from "vue";

import type { ToastMessage, ToastTone } from "../types";

export interface PortalNotifications {
  toast: ReturnType<typeof ref<ToastMessage | null>>;
  notify(message: string, tone?: ToastTone): void;
  dismiss(): void;
}

export function createPortalNotifications(): PortalNotifications {
  const toast = ref<ToastMessage | null>(null);
  let timer: ReturnType<typeof setTimeout> | undefined;

  function dismiss(): void {
    if (timer) clearTimeout(timer);
    timer = undefined;
    toast.value = null;
  }

  function notify(message: string, tone: ToastTone = "info"): void {
    dismiss();
    toast.value = { id: Date.now(), message, tone };
    timer = setTimeout(dismiss, 3000);
  }

  return { toast, notify, dismiss };
}
