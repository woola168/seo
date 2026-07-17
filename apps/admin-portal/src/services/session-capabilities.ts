import type { Capabilities, SessionUser } from "../types";
import { api } from "./api";

let cachedCapabilities: Capabilities | null = null;
let pendingCapabilities: Promise<Capabilities> | null = null;

export function getSessionCapabilities(
  force = false,
): Promise<Capabilities> {
  if (!force && cachedCapabilities) {
    return Promise.resolve(cachedCapabilities);
  }
  if (!force && pendingCapabilities) return pendingCapabilities;

  const request = api.capabilities().then((capabilities) => {
    if (pendingCapabilities === request) cachedCapabilities = capabilities;
    return capabilities;
  });
  pendingCapabilities = request;
  void request.then(
    () => {
      if (pendingCapabilities === request) pendingCapabilities = null;
    },
    () => {
      if (pendingCapabilities === request) pendingCapabilities = null;
    },
  );
  return request;
}

export function clearSessionCapabilities(): void {
  cachedCapabilities = null;
  pendingCapabilities = null;
}

export function refreshSessionCapabilities(): Promise<Capabilities> {
  clearSessionCapabilities();
  return getSessionCapabilities();
}

export function sessionHasRole(
  currentUser: Pick<SessionUser, "roleIds"> | null,
  roleId: string,
): boolean {
  return currentUser?.roleIds.includes(roleId) ?? false;
}
