import { describe, expect, it } from "vitest";
import { useGeoFormErrors } from "./geo-form-errors";

describe("useGeoFormErrors", () => {
  it("sets, clears, and replaces field errors", () => {
    const errors = useGeoFormErrors();

    expect(
      errors.setFormErrors([{ field: "name", message: "請輸入名稱。" }]),
    ).toBe(false);
    expect(errors.formErrors.name).toBe("請輸入名稱。");
    expect(errors.hasFieldError("name")).toBe(true);

    errors.clearFieldError("name");
    expect(errors.formErrors.name).toBeUndefined();

    expect(
      errors.setFormErrors([{ field: "queryId", message: "請選擇 Query。" }]),
    ).toBe(false);
    expect(errors.formErrors.queryId).toBe("請選擇 Query。");

    expect(errors.setFormErrors([])).toBe(true);
    expect(errors.formErrors.queryId).toBeUndefined();
  });
});
