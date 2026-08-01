const CACHE_NAME = 'sir-saathi-app-shell-v5';
const APP_SHELL_URLS = [
  '/',
  '/privacy/',
  '/methodology/',
  '/data-use/',
  '/accessibility/',
  '/manifest.webmanifest',
  '/icons/icon.svg',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon-maskable-512.png',
  '/icons/apple-touch-icon.png'
];
const BUILD_ASSET_URLS = [];
const PRECACHE_URLS = [...new Set([...APP_SHELL_URLS, ...BUILD_ASSET_URLS])];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS)));
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) => Promise.all(keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))))
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const request = event.request;
  const url = new URL(request.url);
  if (request.method !== 'GET' || url.pathname.startsWith('/api/')) {
    return;
  }

  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response.ok && response.type === 'basic') {
          const copy = response.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(async () => {
        const cached = await caches.match(request);
        if (cached) return cached;
        const firstSegment = url.pathname.split('/').filter(Boolean)[0] || '';
        const localizedHome = /^[a-z]{2,3}$/.test(firstSegment)
          ? await caches.match(`/${firstSegment}/`)
          : undefined;
        return localizedHome || caches.match('/');
      })
  );
});
