import { describe, expect, it, vi } from "vitest";

import { useRoleCreationForm } from "./role-creation-form";

describe("useRoleCreationForm", () => {
  it("keeps input until the create success callback runs", () => {
    const form = useRoleCreationForm();
    const create = vi.fn();
    form.roleName.value = "Content Reviewer";
    form.selectedPermissions.value = ["tasks.read"];

    form.submit(create);

    expect(create).toHaveBeenCalledOnce();
    expect(form.roleName.value).toBe("Content Reviewer");
    expect(form.selectedPermissions.value).toEqual(["tasks.read"]);

    const onSuccess = create.mock.calls[0]?.[2];
    onSuccess();

    expect(form.roleName.value).toBe("");
    expect(form.selectedPermissions.value).toEqual([]);
  });
});
