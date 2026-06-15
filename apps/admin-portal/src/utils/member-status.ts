import type { SemanticTone } from "../types";

export interface MemberStatusDisplay {
  value: string;
  label: string;
  tone: SemanticTone;
}

const memberStatuses: Record<string, Omit<MemberStatusDisplay, "value">> = {
  active: { label: "啟用", tone: "success" },
  disabled: { label: "停用", tone: "muted" },
  invited: { label: "邀請中", tone: "blue" },
};

export function getMemberStatusDisplay(status: string): MemberStatusDisplay {
  const display = memberStatuses[status] ?? {
    label: status,
    tone: "muted" as const,
  };
  return { value: status, ...display };
}
