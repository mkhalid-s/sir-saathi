import formsConfig from '../../../../config/forms/sir-actions.json';

interface FormConfig {
  label: string;
  purpose: string;
  official_portal: string;
}

interface FormsConfig {
  forms: Record<string, FormConfig>;
  common_documents: Record<string, string[]>;
}

const catalogue = formsConfig as FormsConfig;

export interface FormSummary {
  formId: string;
  label: string;
  purpose: string;
  officialPortal: string;
}

export const forms: Record<string, FormSummary> = Object.fromEntries(
  Object.entries(catalogue.forms).map(([formId, form]) => [
    formId,
    {
      formId,
      label: form.label,
      purpose: form.purpose,
      officialPortal: form.official_portal
    }
  ])
) as Record<string, FormSummary>;

export const commonDocuments: Record<string, string[]> = catalogue.common_documents;

export function formLabel(formId: string): string {
  return forms[formId]?.label ?? formId;
}

export function documentsFor(...categories: string[]): string[] {
  return categories.flatMap((category) => commonDocuments[category] ?? []);
}
