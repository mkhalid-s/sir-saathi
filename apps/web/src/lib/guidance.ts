import type { StateSummary } from '../data/states';

export type Situation =
  | 'existing_voter'
  | 'missing_name'
  | 'new_voter'
  | 'shifted_address'
  | 'correction'
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

function deadlineNotice(state: StateSummary, situation: Situation): string | undefined {
  const deadline = deadlineFor(state, situation);
  return deadline ? `Use official channels before ${deadline}.` : 'Check the official portal for the latest deadline.';
}

export function deadlineFor(state: StateSummary, situation: Situation): string | undefined {
  if (situation === 'existing_voter' || situation === 'portal_failed') {
    return state.enumerationEnd ?? state.claimsEnd ?? state.finalRollDate;
  }
  return state.claimsEnd ?? state.finalRollDate;
}

export function guidanceFor(input: Situation | WizardAnswers, state?: StateSummary): GuidanceCard {
  const answers = normalizeInput(input);
  const notices = state ? [deadlineNotice(state, answers.situation)].filter(Boolean) as string[] : [];

  if (answers.situation === 'missing_name') {
    const actions = [
      'Search again with alternate spelling, age, district, AC, and family details.',
      'Check the draft/current roll through official channels.',
      'Contact BLO or ERO and keep acknowledgement.',
      'File the appropriate claim before the deadline.'
    ];
    if (answers.baseRollFound === 'yes') {
      actions.splice(2, 0, 'Mention that an older/base-roll record appears to exist when contacting officials.');
    }
    return {
      title: 'Act quickly on a missing name',
      priority: 'urgent',
      summary: 'A missing name during SIR needs fast official follow-up, especially during the claims and objections window.',
      actions,
      documents: ['Identity proof', 'Address proof', 'Previous voter reference if available'],
      notices
    };
  }

  if (answers.situation === 'new_voter') {
    return {
      title: 'Register as a new voter',
      priority: 'high',
      summary: 'Use Form 6 through official online or offline channels if you are eligible and not registered.',
      actions: ['Check eligibility for the qualifying date.', 'Prepare identity, address, and age proof.', 'Submit Form 6 through the official voter portal or ERO/BLO route.'],
      documents: ['Identity proof', 'Address proof', 'Age proof'],
      notices
    };
  }

  if (answers.situation === 'shifted_address') {
    return {
      title: 'Update your shifted address',
      priority: 'high',
      summary: 'Use the official correction or shift workflow so your roll entry matches your current residence.',
      actions: ['Confirm whether the move is within the same AC.', 'Prepare current address proof.', 'Submit Form 8 or the official shift workflow.', 'Verify your updated polling station after disposal.'],
      documents: ['Current address proof', 'Existing voter reference'],
      notices
    };
  }

  if (answers.situation === 'correction') {
    return {
      title: 'Correct voter details',
      priority: 'medium',
      summary: 'Use Form 8 for spelling, age, address, replacement EPIC, or similar corrections.',
      actions: ['Identify the incorrect field.', 'Prepare supporting proof.', 'Submit Form 8 and track the request.'],
      documents: ['Existing voter reference', 'Document supporting the correction'],
      notices
    };
  }

  if (answers.situation === 'portal_failed') {
    return {
      title: 'Use offline fallback if the portal fails',
      priority: 'high',
      summary: 'Portal issues should not block SIR action. Contact BLO or ERO before the deadline.',
      actions: ['Retry the official portal once.', 'Record the error without sharing private details publicly.', 'Submit the relevant form offline and keep acknowledgement.'],
      documents: ['Relevant form details', 'Identity proof', 'Address proof'],
      notices
    };
  }

  const actions = [
    'Verify your name through official sources.',
    'Submit the enumeration form before the deadline if you receive one.',
    'Keep the acknowledgement safely.'
  ];
  let priority: GuidanceCard['priority'] = 'medium';
  if (answers.bloVisited === 'no' || answers.enumerationFormReceived === 'no') {
    actions.unshift('Contact your BLO or local ERO because the enumeration form has not reached you yet.');
    priority = 'high';
  }
  if (answers.enumerationFormReceived === 'yes' && answers.enumerationFormSubmitted === 'no') {
    actions.unshift('Submit the received enumeration form as soon as possible and keep the acknowledgement.');
    priority = 'high';
  }
  if (answers.currentRollFound === 'no') {
    actions.unshift('Treat this as urgent: use the missing-name flow and contact BLO or ERO.');
    priority = 'urgent';
  }

  return {
    title: priority === 'urgent' ? 'Resolve your missing current-roll entry' : 'Verify and submit your SIR details',
    priority,
    summary: 'Confirm your roll entry and complete the SIR enumeration form if you receive one.',
    actions,
    documents: ['Existing voter reference', 'Proof for any changed detail'],
    notices
  };
}
