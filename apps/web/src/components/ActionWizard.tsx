import { useMemo, useState } from 'preact/hooks';
import { states } from '../data/states';
import { deadlineFor, defaultAnswers, guidanceFor, type Situation, type StatusAnswer, type WizardAnswers } from '../lib/guidance';

const situations: { value: Situation; label: string }[] = [
  { value: 'existing_voter', label: 'I am already a voter and want to verify' },
  { value: 'missing_name', label: 'My name is missing or not found' },
  { value: 'new_voter', label: 'I need to register as a new voter' },
  { value: 'shifted_address', label: 'I shifted address' },
  { value: 'correction', label: 'My name, age, or address needs correction' },
  { value: 'deceased_family', label: 'I need to report a deceased family member entry' },
  { value: 'duplicate_entry', label: 'I found a duplicate voter entry' },
  { value: 'portal_failed', label: 'The official portal is not working for me' }
];

const statusOptions: { value: StatusAnswer; label: string }[] = [
  { value: 'unknown', label: 'Not sure' },
  { value: 'yes', label: 'Yes' },
  { value: 'no', label: 'No' }
];

function statusSelect(
  label: string,
  value: StatusAnswer,
  onChange: (value: StatusAnswer) => void
) {
  return (
    <label class="field">
      {label}
      <select class="select" value={value} onChange={(event) => onChange((event.currentTarget as HTMLSelectElement).value as StatusAnswer)}>
        {statusOptions.map((item) => <option value={item.value}>{item.label}</option>)}
      </select>
    </label>
  );
}

export default function ActionWizard() {
  const [stateId, setStateId] = useState('IN-MH');
  const [answers, setAnswers] = useState<WizardAnswers>(defaultAnswers);
  const state = states.find((item) => item.stateId === stateId) ?? states[0];
  const guidance = useMemo(() => guidanceFor(answers, state), [answers, state]);
  const deadline = deadlineFor(state, answers.situation);
  const shareText = `SIR Saathi checklist for ${state.name}: ${guidance.title}. Next: ${guidance.actions[0]} Deadline: ${deadline ?? 'check official portal'}.`;
  const shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
  const updateAnswer = <K extends keyof WizardAnswers>(key: K, value: WizardAnswers[K]) => {
    setAnswers((current) => ({ ...current, [key]: value }));
  };

  return (
    <section class="wizard">
      <div class="form-grid">
        <label class="field">
          State
          <select class="select" value={stateId} onChange={(event) => setStateId((event.currentTarget as HTMLSelectElement).value)}>
            {states.map((item) => <option value={item.stateId}>{item.name}</option>)}
          </select>
        </label>

        <label class="field">
          What is your situation?
          <select class="select" value={answers.situation} onChange={(event) => updateAnswer('situation', (event.currentTarget as HTMLSelectElement).value as Situation)}>
            {situations.map((item) => <option value={item.value}>{item.label}</option>)}
          </select>
        </label>
      </div>

      <div class="question-grid" aria-label="SIR follow-up questions">
        {statusSelect('Did a BLO visit your home?', answers.bloVisited, (value) => updateAnswer('bloVisited', value))}
        {statusSelect('Did you receive an enumeration form?', answers.enumerationFormReceived, (value) => updateAnswer('enumerationFormReceived', value))}
        {statusSelect('Did you submit the enumeration form?', answers.enumerationFormSubmitted, (value) => updateAnswer('enumerationFormSubmitted', value))}
        {statusSelect('Is your name found in the current/draft roll?', answers.currentRollFound, (value) => updateAnswer('currentRollFound', value))}
        {statusSelect('Is your name found in the old/base roll?', answers.baseRollFound, (value) => updateAnswer('baseRollFound', value))}
      </div>

      <div class="result-card priority-${guidance.priority}">
        <p class="result-status">{state.status}</p>
        <h2 class="result-title">{guidance.title}</h2>
        <p class="result-summary">{guidance.summary}</p>
        <p class="deadline">Deadline: {deadline ?? 'Check official portal'}</p>
        <p class="source-note">Sources: {state.sourceLabels.join(', ')}</p>
        <p class="source-note">Schedule source: {state.scheduleProvenance.label} ({state.scheduleProvenance.confidence}).</p>
        <p class="source-note">Sources last checked: {state.sourceFreshness.join('; ')}</p>
        <p class="source-note">Confirm deadlines and eligibility on the official portal before acting.</p>
        <p class="source-note">Languages planned: {state.languages.join(', ')}. Default: {state.defaultLanguage}.</p>
        {!state.publicLaunchReady && <p class="warning-note">Indexed public search is not launch-ready for this state yet. Use official channels for final verification.</p>}
      </div>

      {guidance.notices.length > 0 && (
        <div class="notice-list" aria-label="Important notices">
          {guidance.notices.map((notice) => <p>{notice}</p>)}
        </div>
      )}

      <div class="action-grid">
        <div>
          <h3 class="list-title">Do this next</h3>
          <ol>
            {guidance.actions.map((action) => <li>{action}</li>)}
          </ol>
        </div>
        <div>
          <h3 class="list-title">Keep ready</h3>
          <ul>
            {guidance.documents.map((document) => <li>{document}</li>)}
          </ul>
        </div>
      </div>

      <div class="actions">
        <a class="primary-button" href={state.officialLink} target="_blank" rel="noreferrer">Open official portal</a>
        <a class="secondary-button" href={shareUrl} target="_blank" rel="noreferrer">Share checklist</a>
      </div>
    </section>
  );
}
