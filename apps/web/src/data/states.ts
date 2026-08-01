import maharashtraConfig from '../../../../config/states/IN-MH.json';
import westBengalConfig from '../../../../config/states/IN-WB.json';
import jurisdictionCatalogue from '../../../../config/jurisdictions.json';
import localeCatalogue from '../../../../config/locales.json';
import scheduleCatalogue from '../../../../config/sir-schedules.json';

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
    enumeration_start: string | null;
    enumeration_end: string | null;
    draft_roll_date: string | null;
    claims_start: string | null;
    claims_end: string | null;
    final_roll_date: string | null;
    status: string;
  };
  schedule_provenance: {
    label: string;
    source_type: string;
    confidence: 'official' | 'reported' | 'unverified';
    notes: string;
  };
  ceo_portal: string;
  official_sources: SourceConfig[];
  data_capability: StateCapability;
  public_launch_ready: boolean;
}

interface JurisdictionConfig {
  state_id: string;
  name: string;
  languages: string[];
  default_language: string;
  ceo_portal: string;
}

type ScheduleGroupConfig = StateConfig['sir_schedule'] & {
  state_ids: string[];
  phase: string;
  qualifying_date: string;
  source?: SourceConfig;
};

export interface StateSummary {
  stateId: string;
  name: string;
  languageCodes: string[];
  languages: string[];
  defaultLanguageCode: string;
  defaultLanguage: string;
  capability: StateCapability;
  publicLaunchReady: boolean;
  currentPhase: string;
  status: string;
  enumerationEnd?: string;
  claimsEnd?: string;
  finalRollDate?: string;
  officialLink: string;
  sourceLabels: string[];
  sourceFreshness: string[];
  scheduleProvenance: {
    label: string;
    url: string;
    confidence: 'official' | 'reported' | 'unverified';
    notes: string;
  };
}

export interface UiLanguageOption {
  code: string;
  label: string;
  status: UiLanguageStatus;
}

const localeByCode = localeCatalogue.locales.reduce<Record<string, UiLanguageOption>>(
  (locales, locale) => ({
    ...locales,
    [locale.code]: { code: locale.code, label: locale.label, status: locale.status as UiLanguageStatus }
  }),
  {}
);

const languageNames: Record<string, string> = Object.fromEntries(
  localeCatalogue.locales.map((locale) => [locale.code, locale.label])
);

const statusLabels: Record<string, string> = {
  pre_enumeration: 'Preparing for enumeration',
  enumeration_open: 'Enumeration is open',
  enumeration_scheduled: 'Enumeration scheduled',
  pre_draft_publication: 'Draft roll publication is next',
  claims_and_objections_open: 'Claims and objections are open',
  claims_disposal: 'Claims and objections are being decided',
  final_roll_published: 'Final roll published',
  schedule_pending: 'Schedule to be announced',
  schedule_unverified: 'Schedule not yet verified'
};

function currentIndiaDateIso(): string {
  const parts = new Intl.DateTimeFormat('en', {
    timeZone: 'Asia/Kolkata',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit'
  }).formatToParts(new Date());
  const value = (type: Intl.DateTimeFormatPartTypes) => parts.find((part) => part.type === type)?.value ?? '';
  return `${value('year')}-${value('month')}-${value('day')}`;
}

export function currentPhaseForSchedule(schedule: StateConfig['sir_schedule'], today = currentIndiaDateIso()): string {
  if (schedule.enumeration_start && today < schedule.enumeration_start) return 'pre_enumeration';
  if (schedule.enumeration_start && schedule.enumeration_end && today <= schedule.enumeration_end) return 'enumeration_open';
  if (schedule.draft_roll_date && today < schedule.draft_roll_date) return 'pre_draft_publication';
  if (schedule.draft_roll_date && schedule.claims_end && today <= schedule.claims_end) return 'claims_and_objections_open';
  if (schedule.final_roll_date && today < schedule.final_roll_date) return 'claims_disposal';
  if (schedule.final_roll_date && today >= schedule.final_roll_date) return 'final_roll_published';
  return schedule.status;
}

export function statePath(state: Pick<StateSummary, 'stateId'>): string {
  return `/states/${state.stateId.toLowerCase()}/`;
}

function displayDate(value: string | null): string | undefined {
  if (!value) return undefined;
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium', timeZone: 'Asia/Kolkata' })
    .format(new Date(`${value}T00:00:00+05:30`));
}

function officialLinkFor(config: StateConfig): string {
  const officialSource = config.official_sources.find((source) => source.source_type === 'official_portal');
  return officialSource?.url ?? config.ceo_portal;
}

export function uiLanguageOptionsForState(stateLanguageCodes: string[]): UiLanguageOption[] {
  return ['en', ...stateLanguageCodes.filter((language) => language !== 'en')]
    .map((code) => localeByCode[code])
    .filter((locale): locale is UiLanguageOption => Boolean(locale));
}

function stateFromConfig(config: StateConfig): StateSummary {
  const currentPhase = currentPhaseForSchedule(config.sir_schedule);
  const scheduleSource = config.official_sources.find(
    (source) => source.label === config.schedule_provenance.label
  );
  if (!scheduleSource) throw new Error(`Missing schedule source for ${config.state_id}`);
  return {
    stateId: config.state_id,
    name: config.name,
    languageCodes: config.languages,
    languages: config.languages.map((language) => languageNames[language] ?? language),
    defaultLanguageCode: config.default_language,
    defaultLanguage: languageNames[config.default_language] ?? config.default_language,
    capability: config.data_capability,
    publicLaunchReady: config.public_launch_ready,
    currentPhase,
    status: statusLabels[currentPhase] ?? currentPhase.replaceAll('_', ' '),
    enumerationEnd: displayDate(config.sir_schedule.enumeration_end),
    claimsEnd: displayDate(config.sir_schedule.claims_end),
    finalRollDate: displayDate(config.sir_schedule.final_roll_date),
    officialLink: officialLinkFor(config),
    sourceLabels: config.official_sources.map((source) => source.label),
    sourceFreshness: config.official_sources.map((source) => `${source.label}: last checked ${displayDate(source.last_verified)}`),
    scheduleProvenance: {
      label: config.schedule_provenance.label,
      url: scheduleSource.url,
      confidence: config.schedule_provenance.confidence,
      notes: config.schedule_provenance.notes
    }
  };
}

function stateFromJurisdiction(config: JurisdictionConfig): StateSummary {
  const source = jurisdictionCatalogue.source;
  const baseline: StateSummary = {
    stateId: config.state_id,
    name: config.name,
    languageCodes: config.languages,
    languages: config.languages.map((language) => languageNames[language] ?? language),
    defaultLanguageCode: config.default_language,
    defaultLanguage: languageNames[config.default_language] ?? config.default_language,
    capability: 'official_link_search',
    publicLaunchReady: false,
    currentPhase: 'schedule_unverified',
    status: statusLabels.schedule_unverified,
    officialLink: config.ceo_portal,
    sourceLabels: [`CEO ${config.name}`, 'ECI voters portal', source.label],
    sourceFreshness: [`${source.label}: last checked ${displayDate(source.last_verified)}`],
    scheduleProvenance: {
      label: source.label,
      url: source.url,
      confidence: 'unverified',
      notes: `ECI's directory lists this official CEO link, but ${config.name}'s current SIR schedule has not yet been independently confirmed.`
    }
  };
  const schedule = scheduleByState[config.state_id];
  if (!schedule) return baseline;
  const scheduleSource = schedule.source ?? scheduleCatalogue.source;
  const currentPhase = currentPhaseForSchedule(schedule);
  return {
    ...baseline,
    currentPhase,
    status: statusLabels[currentPhase] ?? currentPhase.replaceAll('_', ' '),
    enumerationEnd: displayDate(schedule.enumeration_end),
    claimsEnd: displayDate(schedule.claims_end),
    finalRollDate: displayDate(schedule.final_roll_date),
    sourceLabels: [scheduleSource.label, ...baseline.sourceLabels],
    sourceFreshness: [
      `${scheduleSource.label}: last checked ${displayDate(scheduleSource.last_verified)}`,
      ...baseline.sourceFreshness
    ],
    scheduleProvenance: {
      label: scheduleSource.label,
      url: scheduleSource.url,
      confidence: 'official',
      notes: scheduleSource.notes ?? ''
    }
  };
}

const scheduleByState = (scheduleCatalogue.schedule_groups as ScheduleGroupConfig[])
  .reduce<Record<string, ScheduleGroupConfig>>((byId, group) => {
    for (const stateId of group.state_ids) {
      if (byId[stateId]) throw new Error(`Duplicate reviewed schedule state: ${stateId}`);
      byId[stateId] = group;
    }
    return byId;
  }, {});

const stateOverrides = [maharashtraConfig, westBengalConfig]
  .map((config) => stateFromConfig(config as StateConfig))
  .reduce<Record<string, StateSummary>>((byId, state) => ({ ...byId, [state.stateId]: state }), {});

export const states: StateSummary[] = (jurisdictionCatalogue.jurisdictions as JurisdictionConfig[])
  .map((config) => stateOverrides[config.state_id] ?? stateFromJurisdiction(config))
  .sort((left, right) => left.name.localeCompare(right.name));
