import { useEffect, useMemo, useState } from 'preact/hooks';
import { states, uiLanguageDirection, uiLanguageOptionsForState } from '../data/states';
import { deadlineFor, defaultAnswers, guidanceFor, type Situation, type StatusAnswer, type WizardAnswers } from '../lib/guidance';
import { hasEnabledCatalogue, translate, type MessageKey, type MessageValues } from '../lib/i18n';
import IndexedSearch from './IndexedSearch';

const situations: { value: Situation; key: MessageKey }[] = [
  { value: 'existing_voter', key: 'wizard.situation.existing_voter' },
  { value: 'missing_name', key: 'wizard.situation.missing_name' },
  { value: 'new_voter', key: 'wizard.situation.new_voter' },
  { value: 'shifted_address', key: 'wizard.situation.shifted_address' },
  { value: 'correction', key: 'wizard.situation.correction' },
  { value: 'deceased_family', key: 'wizard.situation.deceased_family' },
  { value: 'duplicate_entry', key: 'wizard.situation.duplicate_entry' },
  { value: 'portal_failed', key: 'wizard.situation.portal_failed' }
];

const statusOptions: { value: StatusAnswer; key: MessageKey }[] = [
  { value: 'unknown', key: 'wizard.answer.unknown' },
  { value: 'yes', key: 'wizard.answer.yes' },
  { value: 'no', key: 'wizard.answer.no' }
];

const UI_LANGUAGE_STORAGE_KEY = 'sir-saathi-ui-language';

function statusSelect(
  label: string,
  value: StatusAnswer,
  onChange: (value: StatusAnswer) => void,
  message: (key: MessageKey, values?: MessageValues) => string
) {
  return (
    <label class="field">
      {label}
      <select class="select" value={value} onChange={(event) => onChange((event.currentTarget as HTMLSelectElement).value as StatusAnswer)}>
        {statusOptions.map((item) => <option value={item.value}>{message(item.key)}</option>)}
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
  const guidance = useMemo(() => guidanceFor(answers, state, uiLanguage), [answers, state, uiLanguage]);
  const deadline = deadlineFor(state, answers.situation);
  const languageOptions = uiLanguageOptionsForState(state.languageCodes);
  const scheduleKnown = state.currentPhase !== 'schedule_unverified';
  const message = (key: MessageKey, values: MessageValues = {}) => translate(uiLanguage, key, values);
  const plannedLanguages = languageOptions.filter((item) => item.status === 'planned').map((item) => item.label);
  const languageReadiness = plannedLanguages.length
    ? message('wizard.language_planned', { languages: plannedLanguages.join(', ') })
    : message('wizard.language_available');
  const guidanceBoundaryText = message('safety.guidance_boundary');
  const shareSafetyText = `${message('safety.confirm_official')} ${message('safety.no_private_share')}`;
  const shareText = [
    message('share.checklist', { state: state.name, title: guidance.title }),
    message('share.next', { action: guidance.actions[0] }),
    message('share.deadline', { deadline: deadline ?? message('guidance.deadline_unknown') }),
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
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const requestedState = params.get('state');
    if (requestedState && states.some((item) => item.stateId === requestedState)) {
      updateState(requestedState);
    }
    let storedLanguage: string | null = null;
    try {
      storedLanguage = window.localStorage.getItem(UI_LANGUAGE_STORAGE_KEY);
    } catch {
      // Storage can be unavailable in hardened/private browser modes.
    }
    const preferredLanguage = params.get('lang') ?? storedLanguage;
    if (preferredLanguage && hasEnabledCatalogue(preferredLanguage)) {
      setUiLanguage(preferredLanguage);
    }
  }, []);
  useEffect(() => {
    if (!languageOptions.some((item) => item.code === uiLanguage && item.status === 'available')) {
      setUiLanguage('en');
    }
  }, [stateId, uiLanguage]);
  useEffect(() => {
    document.documentElement.lang = uiLanguage;
    document.documentElement.dir = uiLanguageDirection(uiLanguage);
    try {
      window.localStorage.setItem(UI_LANGUAGE_STORAGE_KEY, uiLanguage);
    } catch {
      // Language selection still works for the current page without storage.
    }
    const url = new URL(window.location.href);
    if (uiLanguage === 'en') url.searchParams.delete('lang');
    else url.searchParams.set('lang', uiLanguage);
    window.history.replaceState(window.history.state, '', `${url.pathname}${url.search}${url.hash}`);
    return () => {
      document.documentElement.lang = 'en';
      document.documentElement.dir = 'ltr';
    };
  }, [uiLanguage]);
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
          <p class="eyebrow dark">{message('find.eyebrow')}</p>
          <h2 id="find-name-title">{message('find.title')}</h2>
          <p class="reference-copy" id="find-privacy-notice">{message('find.intro_prefix')} {message('find.privacy_notice')}</p>
        </div>
        <form class="find-form" onSubmit={(event) => {
          event.preventDefault();
          setFindSubmitted(true);
        }}>
          <label class="field">
            {message('find.state_label')}
            <select id="find-state" class="select" value={stateId} onChange={(event) => updateState((event.currentTarget as HTMLSelectElement).value)}>
              {states.map((item) => <option value={item.stateId}>{item.name}</option>)}
            </select>
          </label>
          <label class="field">
            {message('find.name_label')}
            <input id="find-voter-name" class="input" value={nameQuery} onInput={(event) => setNameQuery((event.currentTarget as HTMLInputElement).value)} placeholder={message('find.name_placeholder')} aria-describedby="find-privacy-notice" autoComplete="off" dir="auto" />
          </label>
          <label class="field">
            {message('find.district_label')}
            <input id="find-district" class="input" value={districtHint} onInput={(event) => setDistrictHint((event.currentTarget as HTMLInputElement).value)} placeholder={message('find.optional')} autoComplete="off" dir="auto" />
          </label>
          <label class="field">
            {message('find.ac_label')}
            <input id="find-ac" class="input" value={acHint} onInput={(event) => setAcHint((event.currentTarget as HTMLInputElement).value)} placeholder={message('find.optional')} inputMode="numeric" autoComplete="off" />
          </label>
          <label class="field">
            {message('find.part_label')}
            <input id="find-part" class="input" value={partHint} onInput={(event) => setPartHint((event.currentTarget as HTMLInputElement).value)} placeholder={message('find.optional')} inputMode="numeric" autoComplete="off" />
          </label>
          {state.publicLaunchReady && (
            <IndexedSearch stateId={state.stateId} query={nameQuery} acHint={acHint} partHint={partHint} locale={uiLanguage} />
          )}
          <button class="primary-button" type="submit">{message('find.show_steps')}</button>
        </form>
        {findSubmitted && (
          <div class="find-result" aria-live="polite">
            <h3>{message('find.official_first', { state: state.name })}</h3>
            <p>{message('find.result_intro')}</p>
            <ol class="official-check-steps">
              <li>{message('find.step_state', { state: state.name })}</li>
              <li>{message('find.step_search')}</li>
              <li>{message('find.step_spelling')}</li>
              <li>{message('find.step_contact')}</li>
            </ol>
            <p>{message('find.indexed_boundary')}</p>
            <div class="actions">
              <a class="primary-button" href={state.officialLink} target="_blank" rel="noreferrer">{message('find.open_official')}</a>
              <button class="secondary-button" type="button" onClick={useMissingNameGuidance}>{message('find.not_found')}</button>
              <button class="secondary-button" type="button" onClick={clearFindNameHints}>{message('find.clear')}</button>
            </div>
          </div>
        )}
      </div>

      <div class="form-grid" id="guidance">
        <label class="field">
          {message('wizard.state')}
          <select class="select" value={stateId} onChange={(event) => updateState((event.currentTarget as HTMLSelectElement).value)}>
            {states.map((item) => <option value={item.stateId}>{item.name}</option>)}
          </select>
        </label>

        <label class="field">
          {message('wizard.situation')}
          <select class="select" value={answers.situation} onChange={(event) => updateAnswer('situation', (event.currentTarget as HTMLSelectElement).value as Situation)}>
            {situations.map((item) => <option value={item.value}>{message(item.key)}</option>)}
          </select>
        </label>

        <label class="field">
          {message('wizard.ui_language')}
          <select id="ui-language" class="select" value={uiLanguage} aria-describedby="ui-language-readiness" onChange={(event) => setUiLanguage((event.currentTarget as HTMLSelectElement).value)}>
            {languageOptions.map((item) => <option value={item.code} disabled={item.status === 'planned'}>{item.label}{item.status === 'planned' ? message('wizard.planned_suffix') : ''}</option>)}
          </select>
          <span id="ui-language-readiness" class="field-help">{languageReadiness}</span>
        </label>
      </div>

      <p class="sr-only" aria-live="polite" aria-atomic="true">
        {message('wizard.guidance_updated', { title: guidance.title })}
      </p>

      <div class="question-grid" aria-label={message('wizard.questions_label')}>
        {scheduleKnown && statusSelect(message('wizard.question.blo'), answers.bloVisited, (value) => updateAnswer('bloVisited', value), message)}
        {scheduleKnown && statusSelect(message('wizard.question.received'), answers.enumerationFormReceived, (value) => updateAnswer('enumerationFormReceived', value), message)}
        {scheduleKnown && statusSelect(message('wizard.question.submitted'), answers.enumerationFormSubmitted, (value) => updateAnswer('enumerationFormSubmitted', value), message)}
        {statusSelect(message('wizard.question.current_roll'), answers.currentRollFound, (value) => updateAnswer('currentRollFound', value), message)}
        {scheduleKnown && statusSelect(message('wizard.question.base_roll'), answers.baseRollFound, (value) => updateAnswer('baseRollFound', value), message)}
      </div>

      <div class="result-card priority-${guidance.priority}" aria-labelledby="guidance-result-title">
        <p class="result-status">{message(`status.${state.currentPhase}` as MessageKey)}</p>
        <h2 class="result-title" id="guidance-result-title">{guidance.title}</h2>
        <p class="result-summary">{guidance.summary}</p>
        <p class="source-note">{guidanceBoundaryText}</p>
        <p class="deadline">{message('guidance.deadline', { deadline: deadline ?? message('guidance.deadline_unknown') })}</p>
        <p class="source-note">{message('guidance.sources', { sources: state.sourceLabels.join(', ') })}</p>
        <p class="source-note">{message('guidance.schedule_source', { label: state.scheduleProvenance.label, confidence: state.scheduleProvenance.confidence })}</p>
        <p class="source-note">{message('guidance.schedule_note', { note: state.scheduleProvenance.notes })}</p>
        <p class="source-note">{message('guidance.sources_checked', { sources: state.sourceFreshness.join('; ') })}</p>
        <p class="source-note">{message('safety.confirm_official')}</p>
        <p class="source-note">{message('guidance.language_status', { status: languageReadiness })}</p>
        <p class="source-note">{message('guidance.state_languages', { languages: state.languages.join(', '), default_language: state.defaultLanguage })}</p>
        {!state.publicLaunchReady && <p class="warning-note">{message('safety.search_unavailable')}</p>}
      </div>

      {guidance.notices.length > 0 && (
        <div class="notice-list" aria-label={message('guidance.important_notices')}>
          {guidance.notices.map((notice) => <p>{notice}</p>)}
        </div>
      )}

      <div class="action-grid">
        <div>
          <h3 class="list-title">{message('guidance.next_actions')}</h3>
          <ol>
            {guidance.actions.map((action) => <li>{action}</li>)}
          </ol>
        </div>
        <div>
          <h3 class="list-title">{message('guidance.documents')}</h3>
          <ul>
            {guidance.documents.map((document) => <li>{document}</li>)}
          </ul>
        </div>
      </div>

      <div class="actions">
        <p class="share-note">{shareSafetyText}</p>
        <a class="primary-button" href={state.officialLink} target="_blank" rel="noreferrer">{message('find.open_official')}</a>
        <a class="secondary-button" href={shareUrl} target="_blank" rel="noreferrer">{message('guidance.share')}</a>
      </div>
    </section>
  );
}
