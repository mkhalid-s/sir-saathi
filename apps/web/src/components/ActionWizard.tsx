import { useMemo, useState } from 'preact/hooks';
import { states } from '../data/states';
import { guidanceFor, type Situation } from '../lib/guidance';

const situations: { value: Situation; label: string }[] = [
  { value: 'existing_voter', label: 'I am already a voter and want to verify' },
  { value: 'missing_name', label: 'My name is missing or not found' },
  { value: 'new_voter', label: 'I need to register as a new voter' },
  { value: 'shifted_address', label: 'I shifted address' },
  { value: 'correction', label: 'My name, age, or address needs correction' },
  { value: 'portal_failed', label: 'The official portal is not working for me' }
];

export default function ActionWizard() {
  const [stateId, setStateId] = useState('IN-MH');
  const [situation, setSituation] = useState<Situation>('existing_voter');
  const state = states.find((item) => item.stateId === stateId) ?? states[0];
  const guidance = useMemo(() => guidanceFor(situation), [situation]);
  const deadline = situation === 'existing_voter' || situation === 'portal_failed' ? state.enumerationEnd : state.claimsEnd ?? state.finalRollDate;
  const shareText = `SIR Saathi checklist for ${state.name}: ${guidance.title}. Next: ${guidance.actions[0]} Deadline: ${deadline ?? 'check official portal'}.`;
  const shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;

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
          <select class="select" value={situation} onChange={(event) => setSituation((event.currentTarget as HTMLSelectElement).value as Situation)}>
            {situations.map((item) => <option value={item.value}>{item.label}</option>)}
          </select>
        </label>
      </div>

      <div class="result-card">
        <p class="result-status">{state.status}</p>
        <h2 class="result-title">{guidance.title}</h2>
        <p class="result-summary">{guidance.summary}</p>
        <p class="deadline">Deadline: {deadline ?? 'Check official portal'}</p>
      </div>

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
