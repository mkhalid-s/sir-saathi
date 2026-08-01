import { currentIndiaDateIso, formatIndiaDate, type StateSummary } from '../data/states';
import { translate, type MessageKey, type MessageValues } from './i18n';

export type Situation =
  | 'existing_voter'
  | 'missing_name'
  | 'new_voter'
  | 'shifted_address'
  | 'correction'
  | 'deceased_family'
  | 'duplicate_entry'
  | 'portal_failed';

export type StatusAnswer = 'yes' | 'no' | 'unknown';

export interface WizardAnswers {
  situation: Situation;
  bloVisited: StatusAnswer;
  enumerationFormReceived: StatusAnswer;
  enumerationFormSubmitted: StatusAnswer;
  currentRollFound: StatusAnswer;
  baseRollFound: StatusAnswer;
}

export interface GuidanceCard {
  title: string;
  priority: 'medium' | 'high' | 'urgent';
  summary: string;
  actions: string[];
  documents: string[];
  notices: string[];
}

export const defaultAnswers: WizardAnswers = {
  situation: 'existing_voter',
  bloVisited: 'unknown',
  enumerationFormReceived: 'unknown',
  enumerationFormSubmitted: 'unknown',
  currentRollFound: 'unknown',
  baseRollFound: 'unknown'
};

function normalizeInput(input: Situation | WizardAnswers): WizardAnswers {
  if (typeof input === 'string') {
    return { ...defaultAnswers, situation: input };
  }
  return input;
}

function deadlineNotice(state: StateSummary, situation: Situation, locale: string): string | undefined {
  const deadlineIso = deadlineIsoFor(state, situation);
  if (!deadlineIso) return translate(locale, 'guidance.deadline_latest');
  const remainingDays = Math.round(
    (Date.parse(`${deadlineIso}T00:00:00+05:30`) - Date.parse(`${currentIndiaDateIso()}T00:00:00+05:30`)) /
      (24 * 60 * 60 * 1000)
  );
  if (remainingDays < 0) return translate(locale, 'guidance.warning.passed');
  if (remainingDays <= 3) return translate(locale, 'guidance.warning.close');
  return translate(locale, 'guidance.deadline_before', { deadline: formatIndiaDate(deadlineIso, locale) });
}

export function deadlineIsoFor(state: StateSummary, situation: Situation): string | undefined {
  if (state.currentPhase === 'schedule_unverified' || state.currentPhase === 'schedule_pending') return undefined;
  let value: string | undefined;
  if (situation === 'existing_voter' || situation === 'portal_failed') {
    if (state.currentPhase === 'pre_enumeration' || state.currentPhase === 'enumeration_open') {
      value = state.enumerationEndIso ?? state.claimsEndIso ?? state.finalRollDateIso;
    } else if (state.currentPhase === 'pre_draft_publication' || state.currentPhase === 'claims_and_objections_open') {
      value = state.claimsEndIso ?? state.finalRollDateIso;
    } else {
      value = state.finalRollDateIso;
    }
  } else {
    value = state.currentPhase === 'claims_disposal' || state.currentPhase === 'final_roll_published'
      ? state.finalRollDateIso
      : state.claimsEndIso ?? state.finalRollDateIso;
  }
  return value;
}

export function deadlineFor(state: StateSummary, situation: Situation, locale = 'en-IN'): string | undefined {
  const value = deadlineIsoFor(state, situation);
  return value ? formatIndiaDate(value, locale) : undefined;
}

export function guidanceFor(input: Situation | WizardAnswers, state?: StateSummary, locale = 'en'): GuidanceCard {
  const answers = normalizeInput(input);
  const text = (key: MessageKey, values: MessageValues = {}) => translate(locale, key, values);
  const form = (formId: 'form_6' | 'form_7' | 'form_8') => text(`forms.${formId}.label` as MessageKey);
  const notices = state ? [deadlineNotice(state, answers.situation, locale)].filter(Boolean) as string[] : [];
  const scheduleUnavailable = state?.currentPhase === 'schedule_unverified' || state?.currentPhase === 'schedule_pending';

  if (answers.situation === 'missing_name') {
    const actions = [
      text('guidance.missing.search_again'),
      text('guidance.missing.check_roll'),
      text('guidance.missing.file_claim'),
      text('guidance.missing.contact')
    ];
    if (!scheduleUnavailable && answers.baseRollFound === 'yes') {
      actions.splice(2, 0, text('guidance.missing.base_reference'));
    }
    return {
      title: text('guidance.missing.title'),
      priority: 'urgent',
      summary: text('guidance.missing.summary'),
      actions,
      documents: [text('document.identity'), text('document.address'), text('document.previous_reference')],
      notices
    };
  }

  if (answers.situation === 'new_voter') {
    return {
      title: text('guidance.new.title'),
      priority: 'high',
      summary: text('guidance.new.summary', { form: form('form_6') }),
      actions: [text('guidance.new.eligibility'), text('guidance.new.prepare'), text('guidance.new.submit', { form: form('form_6') }), text('guidance.new.track')],
      documents: [text('document.identity'), text('document.address'), text('document.age')],
      notices
    };
  }

  if (answers.situation === 'shifted_address') {
    return {
      title: text('guidance.shift.title'),
      priority: 'high',
      summary: text('guidance.shift.summary'),
      actions: [text('guidance.shift.confirm_ac'), text('guidance.shift.prepare'), text('guidance.shift.submit', { form: form('form_8') }), text('guidance.shift.verify_station')],
      documents: [text('document.address'), text('document.existing_reference')],
      notices
    };
  }

  if (answers.situation === 'correction') {
    return {
      title: text('guidance.correction.title'),
      priority: 'medium',
      summary: text('guidance.correction.summary', { form: form('form_8') }),
      actions: [text('guidance.correction.identify'), text('guidance.correction.prepare'), text('guidance.correction.submit', { form: form('form_8') })],
      documents: [text('document.existing_reference'), text('document.correction')],
      notices
    };
  }

  if (answers.situation === 'deceased_family') {
    return {
      title: text('guidance.deceased.title'),
      priority: 'medium',
      summary: text('guidance.deceased.summary'),
      actions: [text('guidance.deceased.confirm'), text('guidance.deceased.prepare'), text('guidance.deceased.submit', { form: form('form_7') }), text('guidance.deceased.keep')],
      documents: [text('document.deletion'), text('document.contact')],
      notices
    };
  }

  if (answers.situation === 'duplicate_entry') {
    return {
      title: text('guidance.duplicate.title'),
      priority: 'medium',
      summary: text('guidance.duplicate.summary'),
      actions: [text('guidance.duplicate.note'), text('guidance.duplicate.contact'), text('guidance.duplicate.submit')],
      documents: [text('document.existing_reference'), text('document.address')],
      notices
    };
  }

  if (answers.situation === 'portal_failed') {
    return {
      title: text('guidance.portal.title'),
      priority: 'high',
      summary: text('guidance.portal.summary'),
      actions: [text('guidance.portal.retry'), text('guidance.portal.record'), text('guidance.portal.submit')],
      documents: [text('document.form_details'), text('document.identity'), text('document.address')],
      notices
    };
  }

  const revisionComplete = state?.currentPhase === 'final_roll_published';
  const enumerationActionable = state?.currentPhase === 'pre_enumeration' || state?.currentPhase === 'enumeration_open';
  const actions = scheduleUnavailable
    ? [
        text('guidance.existing.check_current'),
        text('guidance.existing.check_notices'),
        text('guidance.existing.contact_unverified')
      ]
    : revisionComplete
    ? [
        text('guidance.existing.check_final'),
        text('guidance.existing.current_remedy'),
        text('guidance.existing.keep_every')
      ]
    : !enumerationActionable
    ? [
        text('guidance.existing.check_draft'),
        text('guidance.existing.file_claim'),
        text('guidance.existing.keep_every')
      ]
    : [
        text('guidance.existing.verify'),
        text('guidance.existing.submit_enumeration'),
        text('guidance.existing.keep')
      ];
  let priority: GuidanceCard['priority'] = 'medium';
  if (enumerationActionable && (answers.bloVisited === 'no' || answers.enumerationFormReceived === 'no')) {
    actions.unshift(text('guidance.existing.contact_missing_form'));
    priority = 'high';
  }
  if (enumerationActionable && answers.enumerationFormReceived === 'yes' && answers.enumerationFormSubmitted === 'no') {
    actions.unshift(text('guidance.existing.submit_received'));
    priority = 'high';
  }
  if (answers.currentRollFound === 'no') {
    actions.unshift(text('guidance.existing.urgent_missing'));
    priority = 'urgent';
  }

  return {
    title: text(priority === 'urgent' ? 'guidance.existing.title_missing' : 'guidance.existing.title'),
    priority,
    summary: scheduleUnavailable
      ? text('guidance.existing.summary_unverified')
      : revisionComplete
      ? text('guidance.existing.summary_complete')
      : text('guidance.existing.summary'),
    actions,
    documents: [text('document.existing_reference'), text('document.changed_detail')],
    notices
  };
}
