import { describe, expect, it } from "vitest";

import { useEmployeeInvitationForm } from "./employee-invitation-form";

const tasks = [
  {
    id: "task-1",
    customerId: "customer-1",
    customerName: "客戶一",
    name: "任務一",
    status: "active" as const,
  },
  {
    id: "task-2",
    customerId: "customer-2",
    customerName: "客戶二",
    name: "任務二",
    status: "active" as const,
  },
];

describe("employee invitation form", () => {
  it("requires display name, email and at least one role", () => {
    const invitation = useEmployeeInvitationForm(() => tasks);

    expect(invitation.createPayload()).toBeNull();

    invitation.form.displayName = "王小明";
    invitation.form.email = "user@example.com";
    invitation.form.roleIds = ["role-1"];

    expect(invitation.canSubmit.value).toBe(true);
  });

  it("creates the existing invitation payload and removes unavailable tasks", () => {
    const invitation = useEmployeeInvitationForm(() => tasks);
    Object.assign(invitation.form, {
      displayName: " 王小明 ",
      email: " user@example.com ",
      departmentId: "department-1",
      roleIds: ["role-1", "role-2"],
      customerIds: ["customer-1"],
      taskIds: ["task-1", "task-2"],
      sendInvitation: true,
    });

    expect(invitation.createPayload()).toEqual({
      displayName: "王小明",
      email: "user@example.com",
      departmentId: "department-1",
      roleIds: ["role-1", "role-2"],
      customerIds: ["customer-1"],
      taskIds: ["task-1"],
      sendInvitation: true,
    });
  });

  it("hides tasks until at least one customer is selected", () => {
    const invitation = useEmployeeInvitationForm(() => tasks);

    expect(invitation.availableTasks.value).toEqual([]);

    invitation.form.customerIds = ["customer-1"];

    expect(invitation.availableTasks.value.map((task) => task.id)).toEqual([
      "task-1",
    ]);
  });

  it("removes selected tasks when their customer is no longer selected", () => {
    const invitation = useEmployeeInvitationForm(() => tasks);
    invitation.form.customerIds = ["customer-1", "customer-2"];
    invitation.form.taskIds = ["task-1", "task-2"];

    invitation.form.customerIds = ["customer-1"];

    expect(invitation.form.taskIds).toEqual(["task-1"]);
  });

  it("keeps input until reset is called after a successful request", () => {
    const invitation = useEmployeeInvitationForm(() => tasks);
    invitation.form.displayName = "王小明";
    invitation.form.email = "user@example.com";
    invitation.form.roleIds = ["role-1"];

    expect(invitation.form.displayName).toBe("王小明");

    invitation.reset();

    expect(invitation.form.displayName).toBe("");
    expect(invitation.form.email).toBe("");
    expect(invitation.form.roleIds).toEqual([]);
  });
});
