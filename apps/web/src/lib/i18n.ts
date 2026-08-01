import englishCatalog from '../../../../config/translations/en.json';
import localeRegistry from '../../../../config/locales.json';

interface TranslationCatalog {
  locale: string;
  messages: Record<string, string>;
}

export type MessageKey = keyof typeof englishCatalog.messages;
export type MessageValues = Record<string, string | number>;

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

export function hasEnabledCatalogue(locale: string): boolean {
  return enabledLocales.has(locale) && Boolean(catalogues[locale]);
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
