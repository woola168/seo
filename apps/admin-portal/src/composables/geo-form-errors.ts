import { reactive } from "vue";

export interface GeoFormValidationError {
  field: string;
  message: string;
}

export function useGeoFormErrors() {
  const formErrors = reactive<Record<string, string>>({});

  function setFormErrors(errors: GeoFormValidationError[]): boolean {
    clearFormErrors();
    for (const error of errors) {
      formErrors[error.field] = error.message;
    }
    return errors.length === 0;
  }

  function clearFieldError(field: string): void {
    delete formErrors[field];
  }

  function clearFormErrors(): void {
    for (const field of Object.keys(formErrors)) {
      delete formErrors[field];
    }
  }

  function hasFieldError(field: string): boolean {
    return Boolean(formErrors[field]);
  }

  return {
    formErrors,
    setFormErrors,
    clearFieldError,
    clearFormErrors,
    hasFieldError,
  };
}
