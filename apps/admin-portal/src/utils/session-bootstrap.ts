export type RecoveryMode = "request" | "reset" | "accept" | null;

export function shouldRestoreSession(
  recoveryMode: RecoveryMode,
  hasSession: boolean,
): boolean {
  return recoveryMode === null && hasSession;
}
