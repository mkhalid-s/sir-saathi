import englishCatalog from '../../../../config/translations/en.json';
import localeRegistry from '../../../../config/locales.json';

interface TranslationCatalog {
  schema_version: number;
  locale: string;
  review: {
    status: string;
    reviewed_by?: string | null;
    reviewed_at?: string | null;
  };
  messages: Record<string, string>;
}

export type MessageKey = keyof typeof englishCatalog.messages;
export type MessageValues = Record<string, string | number>;
export type UiDirection = 'ltr' | 'rtl';

const discoveredCatalogs = import.meta.glob<TranslationCatalog>(
  '../../../../config/translations/*.json',
  { eager: true, import: 'default' }
);

const catalogues = Object.values(discoveredCatalogs).reduce<Record<string, TranslationCatalog>>(
  (byLocale, catalogue) => ({ ...byLocale, [catalogue.locale]: catalogue }),
  { en: englishCatalog }
);
const enabledLocales = new Set(
  localeRegistry.locales.filter((locale) => locale.status === 'available').map((locale) => locale.code)
);

function placeholders(value: string): string[] {
  return [...value.matchAll(/\{([a-z][a-z0-9_]*)\}/g)].map((match) => match[1]).sort();
}

function catalogueIsRuntimeReady(catalogue: TranslationCatalog): boolean {
  if (catalogue.schema_version !== 1 || !enabledLocales.has(catalogue.locale)) return false;
  const referenceKeys = Object.keys(englishCatalog.messages).sort();
  const candidateKeys = Object.keys(catalogue.messages ?? {}).sort();
  if (referenceKeys.length !== candidateKeys.length || referenceKeys.some((key, index) => key !== candidateKeys[index])) {
    return false;
  }
  if (referenceKeys.some((key) => placeholders(englishCatalog.messages[key]).join('|') !== placeholders(catalogue.messages[key]).join('|'))) {
    return false;
  }
  if (catalogue.locale === 'en') return catalogue.review?.status === 'source';
  const reviewedAt = catalogue.review?.reviewed_at ?? '';
  return catalogue.review?.status === 'reviewed'
    && Boolean(catalogue.review.reviewed_by?.trim())
    && /^\d{4}-\d{2}-\d{2}$/.test(reviewedAt)
    && !Number.isNaN(Date.parse(`${reviewedAt}T00:00:00Z`));
}

export function hasEnabledCatalogue(locale: string): boolean {
  const catalogue = catalogues[locale];
  return Boolean(catalogue && catalogueIsRuntimeReady(catalogue));
}

export const availableLocales = localeRegistry.locales
  .filter((locale) => hasEnabledCatalogue(locale.code))
  .map((locale) => ({
    code: locale.code,
    label: locale.label,
    direction: locale.direction as UiDirection
  }));

export function localizedPath(path: string, locale: string): string {
  const normalized = path.startsWith('/') ? path : `/${path}`;
  return locale === 'en' ? normalized : `/${locale}${normalized}`;
}

export function jurisdictionName(locale: string, stateId: string): string {
  return translate(locale, `jurisdiction.${stateId}` as MessageKey);
}

export function translate(locale: string, key: MessageKey, values: MessageValues = {}): string {
  const catalogue = hasEnabledCatalogue(locale) ? catalogues[locale] : englishCatalog;
  const template = catalogue.messages[key] ?? englishCatalog.messages[key];
  if (!template) throw new Error(`Unknown translation key: ${key}`);
  return template.replace(/\{([a-z][a-z0-9_]*)\}/g, (_placeholder, name: string) => {
    if (!(name in values)) throw new Error(`Missing translation value: ${name}`);
    return String(values[name]);
  });
}
