import { useEffect, useRef, useState } from 'preact/hooks';
import { translate, type MessageKey, type MessageValues } from '../lib/i18n';

interface TurnstileApi {
  render(container: HTMLElement, options: Record<string, unknown>): string;
  remove(widgetId: string): void;
  reset(widgetId: string): void;
}

declare global {
  interface Window { turnstile?: TurnstileApi; }
}

interface SearchResult {
  state_id: string;
  ac_number: number | null;
  part_number: number | null;
  serial_number: number | null;
  display_name: string;
  roll_year: number;
  roll_kind: string;
  data_quality: string;
  source_label: string;
  confidence: number;
  epic_hint: string | null;
}

interface Props {
  stateId: string;
  query: string;
  acHint: string;
  partHint: string;
  locale: string;
}

const SCRIPT_ID = 'sir-saathi-turnstile';
const SCRIPT_URL = 'https://challenges.cloudflare.com/turnstile/v0/api.js?render=explicit';

function isBoundedString(value: unknown, maximum: number, allowEmpty = false): value is string {
  return typeof value === 'string' && value.length <= maximum && (allowEmpty || value.trim().length > 0);
}

function safeSearchResults(payload: unknown, stateId: string, acNumber: number, partNumber: number | null): SearchResult[] | null {
  if (!payload || typeof payload !== 'object' || !('results' in payload) || !Array.isArray(payload.results) || payload.results.length > 10) {
    return null;
  }
  const results: SearchResult[] = [];
  for (const candidate of payload.results) {
    if (!candidate || typeof candidate !== 'object') return null;
    const result = candidate as Record<string, unknown>;
    const validPart = partNumber === null
      ? result.part_number === null || (Number.isInteger(result.part_number) && Number(result.part_number) >= 1 && Number(result.part_number) <= 9999)
      : result.part_number === partNumber;
    const validSerial = result.serial_number === null ||
      (Number.isInteger(result.serial_number) && Number(result.serial_number) >= 1 && Number(result.serial_number) <= 1000000);
    const validEpicHint = result.epic_hint === null ||
      (typeof result.epic_hint === 'string' && /^\*{3}\d{4}$/.test(result.epic_hint));
    if (result.state_id !== stateId || result.ac_number !== acNumber || !validPart || !validSerial ||
        !isBoundedString(result.display_name, 200) || !Number.isInteger(result.roll_year) || Number(result.roll_year) < 1900 || Number(result.roll_year) > 2100 ||
        !isBoundedString(result.roll_kind, 80) || !isBoundedString(result.data_quality, 80) || !isBoundedString(result.source_label, 240) ||
        typeof result.confidence !== 'number' || !Number.isFinite(result.confidence) || result.confidence < 0 || result.confidence > 1 || !validEpicHint) {
      return null;
    }
    results.push(result as unknown as SearchResult);
  }
  return results;
}

function loadTurnstile(): Promise<void> {
  if (window.turnstile) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const existing = document.getElementById(SCRIPT_ID) as HTMLScriptElement | null;
    const script = existing ?? document.createElement('script');
    const timeout = window.setTimeout(() => reject(new Error('Turnstile script timed out')), 10000);
    const finish = (callback: () => void) => {
      window.clearTimeout(timeout);
      callback();
    };
    script.addEventListener('load', () => finish(() => window.turnstile ? resolve() : reject(new Error('Turnstile unavailable'))), { once: true });
    script.addEventListener('error', () => finish(() => {
      script.remove();
      reject(new Error('Turnstile script failed'));
    }), { once: true });
    if (!existing) {
      script.id = SCRIPT_ID;
      script.src = SCRIPT_URL;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
  });
}

export default function IndexedSearch({ stateId, query, acHint, partHint, locale }: Props) {
  const siteKey = import.meta.env.PUBLIC_TURNSTILE_SITE_KEY as string | undefined;
  const widgetContainer = useRef<HTMLDivElement>(null);
  const widgetId = useRef<string | null>(null);
  const activeRequest = useRef<AbortController | null>(null);
  const requestVersion = useRef(0);
  const challengeContext = useRef('');
  const [challengeResponse, setChallengeResponse] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [messageKey, setMessageKey] = useState<MessageKey | null>(null);
  const [searching, setSearching] = useState(false);
  const message = (key: MessageKey, values: MessageValues = {}) => translate(locale, key, values);
  const searchContext = JSON.stringify([stateId, query.trim(), acHint.trim(), partHint.trim()]);
  const currentSearchContext = useRef(searchContext);
  currentSearchContext.current = searchContext;

  useEffect(() => {
    requestVersion.current += 1;
    activeRequest.current?.abort();
    activeRequest.current = null;
    setSearching(false);
    setResults([]);
    setMessageKey(null);
    challengeContext.current = '';
    setChallengeResponse('');
    if (widgetId.current && window.turnstile) window.turnstile.reset(widgetId.current);
  }, [stateId, query, acHint, partHint]);

  useEffect(() => () => activeRequest.current?.abort(), []);

  useEffect(() => {
    if (!siteKey || !widgetContainer.current) return;
    let active = true;
    loadTurnstile().then(() => {
      if (!active || !window.turnstile || !widgetContainer.current) return;
      widgetId.current = window.turnstile.render(widgetContainer.current, {
        sitekey: siteKey,
        action: 'voter_search',
        theme: 'auto',
        size: 'flexible',
        language: 'auto',
        callback: (response: string) => {
          challengeContext.current = currentSearchContext.current;
          setChallengeResponse(response);
        },
        'expired-callback': () => {
          challengeContext.current = '';
          setChallengeResponse('');
        },
        'timeout-callback': () => {
          challengeContext.current = '';
          setChallengeResponse('');
        },
        'error-callback': () => {
          challengeContext.current = '';
          setChallengeResponse('');
          setMessageKey('search.error_unavailable');
        }
      });
    }).catch(() => active && setMessageKey('search.error_unavailable'));
    return () => {
      active = false;
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = null;
      challengeContext.current = '';
      setChallengeResponse('');
    };
  }, [siteKey, stateId]);

  const search = async () => {
    const normalizedQuery = query.trim();
    const acNumber = /^\d+$/.test(acHint.trim()) ? Number(acHint) : 0;
    const normalizedPart = partHint.trim();
    const partNumber = /^\d+$/.test(normalizedPart) ? Number(normalizedPart) : null;
    if (normalizedQuery.length < 2 || normalizedQuery.length > 80 || acNumber < 1 || acNumber > 999 ||
        (normalizedPart && (!partNumber || partNumber > 9999))) {
      setMessageKey('search.invalid_scope');
      return;
    }
    if (!challengeResponse || challengeContext.current !== searchContext) {
      setMessageKey('search.verify');
      return;
    }
    activeRequest.current?.abort();
    const controller = new AbortController();
    activeRequest.current = controller;
    const version = ++requestVersion.current;
    const submittedContext = searchContext;
    setSearching(true);
    setMessageKey(null);
    setResults([]);
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          state_id: stateId,
          query: normalizedQuery,
          ac_number: acNumber,
          ...(partNumber ? { part_number: partNumber } : {}),
          limit: 10,
          turnstile_response: challengeResponse
        })
      });
      if (controller.signal.aborted || version !== requestVersion.current || submittedContext !== currentSearchContext.current) return;
      if (!response.ok) {
        setMessageKey(response.status === 429 ? 'search.error_rate' : response.status === 503 ? 'search.error_unavailable' : 'search.error_generic');
        return;
      }
      const payload: unknown = await response.json();
      if (controller.signal.aborted || version !== requestVersion.current || submittedContext !== currentSearchContext.current) return;
      const safeResults = safeSearchResults(payload, stateId, acNumber, partNumber);
      if (safeResults === null) {
        setMessageKey('search.error_generic');
        return;
      }
      setResults(safeResults);
      setMessageKey(safeResults.length ? null : 'search.no_results');
    } catch (error) {
      if ((error as { name?: string })?.name === 'AbortError') return;
      setMessageKey('search.error_unavailable');
    } finally {
      if (version === requestVersion.current && submittedContext === currentSearchContext.current) {
        activeRequest.current = null;
        setSearching(false);
        challengeContext.current = '';
        setChallengeResponse('');
        if (widgetId.current && window.turnstile) window.turnstile.reset(widgetId.current);
      }
    }
  };

  return (
    <div class="indexed-search" aria-labelledby="indexed-search-title">
      <h3 id="indexed-search-title">{message('search.indexed_title')}</h3>
      <p class="reference-copy" id="indexed-search-notice">{message('search.indexed_notice')}</p>
      {!siteKey ? <p class="warning-note" role="status">{message('search.site_key_missing')}</p> : (
        <>
          <p>{message('search.verify')}</p>
          <div ref={widgetContainer} aria-label={message('search.verify')} />
          <button class="primary-button" type="button" aria-describedby="indexed-search-notice" disabled={searching || !challengeResponse} onClick={search}>
            {message(searching ? 'search.searching' : 'search.submit')}
          </button>
        </>
      )}
      <div aria-live="polite" aria-atomic="true" aria-busy={searching}>
        {messageKey && <p class="warning-note">{message(messageKey)}</p>}
        {results.length > 0 && <div class="find-result">
          <h3>{message('search.results')}</h3>
          <ul>{results.map((result) => <li key={`${result.roll_year}-${result.ac_number}-${result.part_number}-${result.serial_number}`}>
            <strong dir="auto">{result.display_name}</strong><br />
            {message('search.result_roll', { year: result.roll_year, kind: result.roll_kind.replaceAll('_', ' ') })}<br />
            {message('search.result_location', { ac: result.ac_number ?? '—', part: result.part_number ?? '—', serial: result.serial_number ?? '—' })}<br />
            {result.epic_hint && message('search.result_epic_hint', { hint: result.epic_hint })}<br />
            <small>{result.source_label}</small>
          </li>)}</ul>
        </div>}
      </div>
    </div>
  );
}
