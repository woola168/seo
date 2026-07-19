import { describe, expect, it } from "vitest";

import { problemInvalidParams, problemMessage } from "./problem-details";

describe("problemMessage", () => {
  it("returns the Problem Details detail message", () => {
    expect(problemMessage({ detail: "The request could not be processed." })).toBe(
      "The request could not be processed.",
    );
  });

  it("formats FastAPI validation issues", () => {
    expect(
      problemMessage({
        detail: [
          {
            loc: ["body", "resource", "id"],
            type: "uuid_parsing",
            msg: "Input should be a valid UUID",
          },
          {
            loc: ["body", "resource", "customerId"],
            type: "uuid_parsing",
            msg: "Input should be a valid UUID",
          },
        ],
      }),
    ).toBe(
      "resource.id: 請輸入有效的 UUID；resource.customerId: 請輸入有效的 UUID",
    );
  });

  it("uses a fallback for unknown payloads", () => {
    expect(problemMessage(null)).toBe("API request failed");
  });

  it("extracts RFC 7807 invalid parameters", () => {
    expect(problemInvalidParams({
      invalidParams: [
        { name: "body.maxQueries", reason: "must be less than or equal to 40", type: "less_than_equal" },
        { name: 123, reason: "ignored" },
      ],
    })).toEqual([
      {
        name: "body.maxQueries",
        reason: "must be less than or equal to 40",
        type: "less_than_equal",
      },
    ]);
  });
});
