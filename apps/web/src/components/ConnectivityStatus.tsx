import { useEffect, useState } from 'preact/hooks';
import { translate } from '../lib/i18n';

interface Props {
  locale: string;
}

export default function ConnectivityStatus({ locale }: Props) {
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    const update = () => setOffline(!navigator.onLine);
    update();
    window.addEventListener('online', update);
    window.addEventListener('offline', update);
    return () => {
      window.removeEventListener('online', update);
      window.removeEventListener('offline', update);
    };
  }, []);

  if (!offline) return null;
  return (
    <aside class="connectivity-notice" role="status" aria-live="polite">
      {translate(locale, 'connectivity.offline')}
    </aside>
  );
}
