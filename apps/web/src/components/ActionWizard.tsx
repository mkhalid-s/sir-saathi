import { useMemo, useState } from 'preact/hooks';
import { states, uiLanguageOptionsForState, uiLanguageReadiness } from '../data/states';
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
  const [uiLanguage, setUiLanguage] = useState('en');
  const [nameQuery, setNameQuery] = useState('');
  const [districtHint, setDistrictHint] = useState('');
  const [acHint, setAcHint] = useState('');
  const [partHint, setPartHint] = useState('');
  const [findSubmitted, setFindSubmitted] = useState(false);
  const [answers, setAnswers] = useState<WizardAnswers>(defaultAnswers);
  const state = states.find((item) => item.stateId === stateId) ?? states[0];
  const guidance = useMemo(() => guidanceFor(answers, state), [answers, state]);
  const deadline = deadlineFor(state, answers.situation);
  const languageOptions = uiLanguageOptionsForState(state.languages);
  const languageReadiness = uiLanguageReadiness(state.languages);
  const guidanceBoundaryText = 'Guidance only: SIR Saathi does not decide voter eligibility or replace official ECI, CEO, BLO, or ERO channels.';
  const shareSafetyText = 'Confirm deadlines and eligibility on the official portal. Do not include EPIC, address, or other private details when forwarding.';
  const shareText = [
    `SIR Saathi checklist for ${state.name}: ${guidance.title}.`,
    `Next: ${guidance.actions[0]}`,
    `Deadline: ${deadline ?? 'check official portal'}.`,
    shareSafetyText
  ].join(' ');
  const shareUrl = `https://wa.me/?text=${encodeURIComponent(shareText)}`;
  const updateAnswer = <K extends keyof WizardAnswers>(key: K, value: WizardAnswers[K]) => {
    setAnswers((current) => ({ ...current, [key]: value }));
  };
  const updateState = (value: string) => {
    setStateId(value);
    setFindSubmitted(false);
  };
  const clearFindNameHints = () => {
    setNameQuery('');
    setDistrictHint('');
    setAcHint('');
    setPartHint('');
    setFindSubmitted(false);
  };
  const useMissingNameGuidance = () => {
    setAnswers((current) => ({
      ...current,
      situation: 'missing_name',
      currentRollFound: 'no'
    }));
  };

  return (
    <section class="wizard" id="find-name">
      <div class="find-flow" aria-labelledby="find-name-title">
        <div>
          <p class="eyebrow dark">Find my name</p>
          <h2 id="find-name-title">Start with a safe official check.</h2>
          <p class="reference-copy">Enter only the hints you would use on the official portal. This MVP fallback does not send these details to SIR Saathi servers, call indexed search, or expose public voter records.</p>
        </div>
        <form class="find-form" onSubmit={(event) => {
          event.preventDefault();
          setFindSubmitted(true);
        }}>
          <label class="field">
            State for official check
            <select class="select" value={stateId} onChange={(event) => updateState((event.currentTarget as HTMLSelectElement).value)}>
              {states.map((item) => <option value={item.stateId}>{item.name}</option>)}
            </select>
          </label>
          <label class="field">
            Name to check
            <input class="input" value={nameQuery} onInput={(event) => setNameQuery((event.currentTarget as HTMLInputElement).value)} placeholder="Name as it may appear in the roll" />
          </label>
          <label class="field">
            District or city if known
            <input class="input" value={districtHint} onInput={(event) => setDistrictHint((event.currentTarget as HTMLInputElement).value)} placeholder="Optional" />
          </label>
          <label class="field">
            Assembly Constituency if known
            <input class="input" value={acHint} onInput={(event) => setAcHint((event.currentTarget as HTMLInputElement).value)} placeholder="Optional" />
          </label>
          <label class="field">
            Part number if known
            <input class="input" value={partHint} onInput={(event) => setPartHint((event.currentTarget as HTMLInputElement).value)} placeholder="Optional" />
          </label>
          <button class="primary-button" type="submit">Show official check steps</button>
        </form>
        {findSubmitted && (
          <div class="find-result" aria-live="polite">
            <h3>Use official search first for {state.name}</h3>
            <p>Open the official portal and search with your name plus district, AC, or part number if you know them. Confirm any match on the official portal before acting.</p>
            <ol class="official-check-steps">
              <li>Select {state.name} or the matching state section on the official portal.</li>
              <li>Search with the name as it may appear in the roll, then narrow with district, AC, or part number if known.</li>
              <li>Try common spelling variations before assuming the name is missing.</li>
              <li>If there is still no official match, use the missing-name steps below and contact BLO or ERO.</li>
            </ol>
            <p>Indexed public search is not used here unless a state passes launch readiness, official schedule provenance, privacy, and abuse checks.</p>
            <div class="actions">
              <a class="primary-button" href={state.officialLink} target="_blank" rel="noreferrer">Open official portal</a>
              <button class="secondary-button" type="button" onClick={useMissingNameGuidance}>If not found, show missing-name steps</button>
              <button class="secondary-button" type="button" onClick={clearFindNameHints}>Clear entered details</button>
            </div>
          </div>
        )}
      </div>

      <div class="form-grid" id="guidance">
        <label class="field">
          State
          <select class="select" value={stateId} onChange={(event) => updateState((event.currentTarget as HTMLSelectElement).value)}>
            {states.map((item) => <option value={item.stateId}>{item.name}</option>)}
          </select>
        </label>

        <label class="field">
          What is your situation?
          <select class="select" value={answers.situation} onChange={(event) => updateAnswer('situation', (event.currentTarget as HTMLSelectElement).value as Situation)}>
            {situations.map((item) => <option value={item.value}>{item.label}</option>)}
          </select>
        </label>

        <label class="field">
          UI language
          <select class="select" value={uiLanguage} onChange={(event) => setUiLanguage((event.currentTarget as HTMLSelectElement).value)}>
            {languageOptions.map((item) => <option value={item.code} disabled={item.status === 'planned'}>{item.label}{item.status === 'planned' ? ' (planned)' : ''}</option>)}
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
        <p class="source-note">{guidanceBoundaryText}</p>
        <p class="deadline">Deadline: {deadline ?? 'Check official portal'}</p>
        <p class="source-note">Sources: {state.sourceLabels.join(', ')}</p>
        <p class="source-note">Schedule source: {state.scheduleProvenance.label} ({state.scheduleProvenance.confidence}).</p>
        <p class="source-note">Schedule note: {state.scheduleProvenance.notes}</p>
        <p class="source-note">Sources last checked: {state.sourceFreshness.join('; ')}</p>
        <p class="source-note">Confirm deadlines and eligibility on the official portal before acting.</p>
        <p class="source-note">UI language status: {languageReadiness}</p>
        <p class="source-note">State languages tracked: {state.languages.join(', ')}. Default: {state.defaultLanguage}.</p>
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
        <p class="share-note">{shareSafetyText}</p>
        <a class="primary-button" href={state.officialLink} target="_blank" rel="noreferrer">Open official portal</a>
        <a class="secondary-button" href={shareUrl} target="_blank" rel="noreferrer">Share checklist</a>
      </div>
    </section>
  );
}
