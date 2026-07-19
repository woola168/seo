type ProblemDetail = {
  detail?: unknown;
  invalidParams?: unknown;
  message?: unknown;
  title?: unknown;
};

export interface ProblemInvalidParam {
  name: string;
  reason: string;
  type?: string;
}

export function problemInvalidParams(payload: unknown): ProblemInvalidParam[] {
  if (!isRecord(payload) || !Array.isArray(payload.invalidParams)) return [];
  return payload.invalidParams.flatMap((item) => {
    if (!isRecord(item) || typeof item.name !== "string" || typeof item.reason !== "string") {
      return [];
    }
    return [{
      name: item.name,
      reason: item.reason,
      ...(typeof item.type === "string" ? { type: item.type } : {}),
    }];
  });
}

type ValidationIssue = {
  loc?: unknown;
  msg?: unknown;
  type?: unknown;
};

export function problemMessage(payload: unknown): string {
  if (!isRecord(payload)) return "API request failed";

  const problem = payload as ProblemDetail;
  if (typeof problem.detail === "string" && problem.detail.trim()) {
    return problem.detail;
  }

  if (Array.isArray(problem.detail)) {
    const messages = problem.detail
      .map(validationIssueMessage)
      .filter((message): message is string => Boolean(message));
    if (messages.length) return messages.join("；");
  }

  for (const fallback of [problem.message, problem.title]) {
    if (typeof fallback === "string" && fallback.trim()) return fallback;
  }
  return "API request failed";
}

function validationIssueMessage(issue: unknown): string | null {
  if (!isRecord(issue)) return null;

  const validationIssue = issue as ValidationIssue;
  const message =
    validationIssue.type === "uuid_parsing"
      ? "請輸入有效的 UUID"
      : typeof validationIssue.msg === "string"
        ? validationIssue.msg.trim()
        : "";
  if (!message) return null;

  const location = Array.isArray(validationIssue.loc)
    ? validationIssue.loc
        .filter(
          (part): part is string | number =>
            typeof part === "string" || typeof part === "number",
        )
        .filter((part) => part !== "body")
        .join(".")
    : "";
  return location ? `${location}: ${message}` : message;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
