import { ref } from "vue";

export type CreateRoleRequest = (
  name: string,
  permissions: string[],
  onSuccess: () => void,
) => void;

export function useRoleCreationForm() {
  const roleName = ref("");
  const selectedPermissions = ref<string[]>([]);

  function reset(): void {
    roleName.value = "";
    selectedPermissions.value = [];
  }

  function submit(create: CreateRoleRequest): void {
    const name = roleName.value.trim();
    if (!name) return;
    create(name, [...selectedPermissions.value], reset);
  }

  return {
    roleName,
    selectedPermissions,
    submit,
  };
}
