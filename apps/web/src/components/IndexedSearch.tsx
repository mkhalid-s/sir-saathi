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
  const [challengeResponse, setChallengeResponse] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [messageKey, setMessageKey] = useState<MessageKey | null>(null);
  const [searching, setSearching] = useState(false);
  const message = (key: MessageKey, values: MessageValues = {}) => translate(locale, key, values);

  useEffect(() => {
    setResults([]);
    setMessageKey(null);
  }, [stateId, query, acHint, partHint]);

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
        callback: (response: string) => setChallengeResponse(response),
        'expired-callback': () => setChallengeResponse(''),
        'timeout-callback': () => setChallengeResponse(''),
        'error-callback': () => {
          setChallengeResponse('');
          setMessageKey('search.error_unavailable');
        }
      });
    }).catch(() => active && setMessageKey('search.error_unavailable'));
    return () => {
      active = false;
      if (widgetId.current && window.turnstile) window.turnstile.remove(widgetId.current);
      widgetId.current = null;
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
    if (!challengeResponse) {
      setMessageKey('search.verify');
      return;
    }
    setSearching(true);
    setMessageKey(null);
    setResults([]);
    try {
      const response = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          state_id: stateId,
          query: normalizedQuery,
          ac_number: acNumber,
          ...(partNumber ? { part_number: partNumber } : {}),
          limit: 10,
          turnstile_response: challengeResponse
        })
      });
      if (!response.ok) {
        setMessageKey(response.status === 429 ? 'search.error_rate' : response.status === 503 ? 'search.error_unavailable' : 'search.error_generic');
        return;
      }
      const payload = await response.json() as { results?: SearchResult[] };
      const safeResults = Array.isArray(payload.results) ? payload.results.slice(0, 10) : [];
      setResults(safeResults);
      setMessageKey(safeResults.length ? null : 'search.no_results');
    } catch {
      setMessageKey('search.error_unavailable');
    } finally {
      setSearching(false);
      setChallengeResponse('');
      if (widgetId.current && window.turnstile) window.turnstile.reset(widgetId.current);
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
