const REMEMBERED_LOGIN_EMAIL_KEY = "adminPortal:rememberedLoginEmail";

function getStorage(): Storage | null {
  try {
    return globalThis.localStorage ?? null;
  } catch {
    return null;
  }
}

export function getRememberedLoginEmail(): string {
  try {
    return getStorage()?.getItem(REMEMBERED_LOGIN_EMAIL_KEY)?.trim() ?? "";
  } catch {
    return "";
  }
}

export function updateRememberedLoginEmail(
  email: string,
  rememberEmail: boolean,
): void {
  try {
    const storage = getStorage();
    if (!storage) return;
    const normalizedEmail = email.trim();
    if (rememberEmail && normalizedEmail) {
      storage.setItem(REMEMBERED_LOGIN_EMAIL_KEY, normalizedEmail);
    } else {
      storage.removeItem(REMEMBERED_LOGIN_EMAIL_KEY);
    }
  } catch {
    // 瀏覽器隱私設定可能停用 storage，但不應阻擋登入。
  }
}
