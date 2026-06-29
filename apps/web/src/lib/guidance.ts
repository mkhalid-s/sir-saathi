export type Situation =
  | 'existing_voter'
  | 'missing_name'
  | 'new_voter'
  | 'shifted_address'
  | 'correction'
  | 'portal_failed';

export interface GuidanceCard {
  title: string;
  priority: 'medium' | 'high' | 'urgent';
  summary: string;
  actions: string[];
  documents: string[];
}

export function guidanceFor(situation: Situation): GuidanceCard {
  switch (situation) {
    case 'missing_name':
      return {
        title: 'Act quickly on a missing name',
        priority: 'urgent',
        summary: 'Search again through official channels, then use the claims and objections route if your name is still missing.',
        actions: ['Search with alternate spelling and AC details.', 'Check the draft/current roll on the official portal.', 'Contact BLO or ERO and keep acknowledgement.', 'File the appropriate claim before the deadline.'],
        documents: ['Identity proof', 'Address proof', 'Previous voter reference if available']
      };
    case 'new_voter':
      return {
        title: 'Register as a new voter',
        priority: 'high',
        summary: 'Use Form 6 through official online or offline channels if you are eligible and not registered.',
        actions: ['Check eligibility for the qualifying date.', 'Prepare identity, address, and age proof.', 'Submit Form 6 through the official voter portal or ERO/BLO route.'],
        documents: ['Identity proof', 'Address proof', 'Age proof']
      };
    case 'shifted_address':
      return {
        title: 'Update your shifted address',
        priority: 'high',
        summary: 'Use the official correction or shift workflow so your roll entry matches your current residence.',
        actions: ['Confirm whether the move is within the same AC.', 'Prepare current address proof.', 'Submit Form 8 or the official shift workflow.'],
        documents: ['Current address proof', 'Existing voter reference']
      };
    case 'correction':
      return {
        title: 'Correct voter details',
        priority: 'medium',
        summary: 'Use Form 8 for spelling, age, address, replacement EPIC, or similar corrections.',
        actions: ['Identify the incorrect field.', 'Prepare supporting proof.', 'Submit Form 8 and track the request.'],
        documents: ['Existing voter reference', 'Document supporting the correction']
      };
    case 'portal_failed':
      return {
        title: 'Use offline fallback if the portal fails',
        priority: 'high',
        summary: 'Portal issues should not block SIR action. Contact BLO or ERO before the deadline.',
        actions: ['Retry the official portal once.', 'Record the error without sharing private details publicly.', 'Submit the relevant form offline and keep acknowledgement.'],
        documents: ['Relevant form details', 'Identity proof', 'Address proof']
      };
    default:
      return {
        title: 'Verify and submit your SIR details',
        priority: 'medium',
        summary: 'Confirm your roll entry and complete the SIR enumeration form if you receive one.',
        actions: ['Verify your name through official sources.', 'Submit the enumeration form before the deadline.', 'Keep the acknowledgement safely.'],
        documents: ['Existing voter reference', 'Proof for any changed detail']
      };
  }
}
