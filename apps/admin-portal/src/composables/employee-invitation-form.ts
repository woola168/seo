import { computed, reactive, watch } from "vue";

import type { CreateInvitationInput, TaskSummary } from "../types";

export function useEmployeeInvitationForm(tasks: () => TaskSummary[]) {
  const form = reactive<CreateInvitationInput>(createInitialForm());

  const availableTasks = computed(() =>
    form.customerIds.length
      ? tasks().filter((task) => form.customerIds.includes(task.customerId))
      : [],
  );

  watch(availableTasks, (items) => {
    const availableTaskIds = new Set(items.map((task) => task.id));
    form.taskIds = form.taskIds.filter((taskId) =>
      availableTaskIds.has(taskId),
    );
  }, { flush: "sync" });

  const canSubmit = computed(
    () =>
      Boolean(form.email.trim()) &&
      Boolean(form.displayName.trim()) &&
      form.roleIds.length > 0,
  );

  function createPayload(): CreateInvitationInput | null {
    if (!canSubmit.value) return null;

    const availableTaskIds = new Set(
      availableTasks.value.map((task) => task.id),
    );

    return {
      ...form,
      email: form.email.trim(),
      displayName: form.displayName.trim(),
      taskIds: form.taskIds.filter((taskId) => availableTaskIds.has(taskId)),
    };
  }

  function reset(): void {
    Object.assign(form, createInitialForm());
  }

  return {
    form,
    availableTasks,
    canSubmit,
    createPayload,
    reset,
  };
}

function createInitialForm(): CreateInvitationInput {
  return {
    email: "",
    displayName: "",
    departmentId: null,
    roleIds: [],
    customerIds: [],
    taskIds: [],
    sendInvitation: true,
  };
}
