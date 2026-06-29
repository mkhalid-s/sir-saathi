import maharashtraConfig from '../../../../config/states/IN-MH.json';
import westBengalConfig from '../../../../config/states/IN-WB.json';

export type StateCapability = 'guidance_only' | 'official_link_search' | 'pilot_indexed_search' | 'validated_indexed_search';
export type UiLanguageStatus = 'available' | 'planned';

interface SourceConfig {
  label: string;
  url: string;
  source_type: string;
  last_verified: string;
  notes?: string;
}

interface StateConfig {
  state_id: string;
  name: string;
  languages: string[];
  default_language: string;
  sir_schedule: {
    enumeration_end: string | null;
    claims_end: string | null;
    final_roll_date: string | null;
    status: string;
  };
  schedule_provenance: {
    label: string;
    source_type: string;
    confidence: 'official' | 'reported';
    notes: string;
  };
  ceo_portal: string;
  official_sources: SourceConfig[];
  data_capability: StateCapability;
  public_launch_ready: boolean;
}

export interface StateSummary {
  stateId: string;
  name: string;
  languages: string[];
  defaultLanguage: string;
  capability: StateCapability;
  publicLaunchReady: boolean;
  status: string;
  enumerationEnd?: string;
  claimsEnd?: string;
  finalRollDate?: string;
  officialLink: string;
  sourceLabels: string[];
  sourceFreshness: string[];
  scheduleProvenance: {
    label: string;
    confidence: 'official' | 'reported';
    notes: string;
  };
}

export interface UiLanguageOption {
  code: string;
  label: string;
  status: UiLanguageStatus;
}

const ENGLISH_LABEL = 'English';

const languageNames: Record<string, string> = {
  bn: 'Bengali',
  en: 'English',
  hi: 'Hindi',
  mr: 'Marathi'
};

const statusLabels: Record<string, string> = {
  enumeration_scheduled: 'Enumeration scheduled',
  final_roll_published: 'Final roll published'
};

function displayDate(value: string | null): string | undefined {
  if (!value) return undefined;
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(new Date(`${value}T00:00:00+05:30`));
}

function officialLinkFor(config: StateConfig): string {
  const officialSource = config.official_sources.find((source) => source.source_type === 'official_portal');
  return officialSource?.url ?? config.ceo_portal;
}

export function uiLanguageOptionsForState(stateLanguages: string[]): UiLanguageOption[] {
  const plannedLanguages = stateLanguages.filter((language) => language !== ENGLISH_LABEL);
  return [
    { code: 'en', label: ENGLISH_LABEL, status: 'available' },
    ...plannedLanguages.map((language) => ({
      code: language.toLowerCase(),
      label: language,
      status: 'planned' as const
    }))
  ];
}

export function uiLanguageReadiness(stateLanguages: string[]): string {
  const plannedLanguages = stateLanguages.filter((language) => language !== ENGLISH_LABEL);
  if (plannedLanguages.length === 0) {
    return 'English UI is available now.';
  }
  return `English UI is available now. ${plannedLanguages.join(', ')} translations are planned and will be added after human review.`;
}

function stateFromConfig(config: StateConfig): StateSummary {
  return {
    stateId: config.state_id,
    name: config.name,
    languages: config.languages.map((language) => languageNames[language] ?? language),
    defaultLanguage: languageNames[config.default_language] ?? config.default_language,
    capability: config.data_capability,
    publicLaunchReady: config.public_launch_ready,
    status: statusLabels[config.sir_schedule.status] ?? config.sir_schedule.status.replaceAll('_', ' '),
    enumerationEnd: displayDate(config.sir_schedule.enumeration_end),
    claimsEnd: displayDate(config.sir_schedule.claims_end),
    finalRollDate: displayDate(config.sir_schedule.final_roll_date),
    officialLink: officialLinkFor(config),
    sourceLabels: config.official_sources.map((source) => source.label),
    sourceFreshness: config.official_sources.map((source) => `${source.label}: last checked ${displayDate(source.last_verified)}`),
    scheduleProvenance: {
      label: config.schedule_provenance.label,
      confidence: config.schedule_provenance.confidence,
      notes: config.schedule_provenance.notes
    }
  };
}

export const states: StateSummary[] = [maharashtraConfig, westBengalConfig].map((config) => stateFromConfig(config as StateConfig));
