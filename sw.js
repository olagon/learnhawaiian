// Service worker for ʻŌlelo Daily
// Caches the app shell and data file for offline use.
// Network-first for HTML so users get fresh content; cache-first for static assets.

const CACHE_NAME = 'olelo-daily-v1';
const ASSETS = [
    './',
    './index.html',
    './data.js',
    './manifest.json'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys => Promise.all(
            keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
        )).then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const req = event.request;
    if (req.method !== 'GET') return;
    const url = new URL(req.url);
    // Only cache same-origin requests; let everything else pass through (Supabase, fonts, CDN)
    if (url.origin !== self.location.origin) return;

    // Network-first for HTML, falling back to cache for offline
    if (req.headers.get('accept') && req.headers.get('accept').includes('text/html')) {
        event.respondWith(
            fetch(req).then(resp => {
                const copy = resp.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
                return resp;
            }).catch(() => caches.match(req).then(r => r || caches.match('./index.html')))
        );
        return;
    }

    // Cache-first for static assets
    event.respondWith(
        caches.match(req).then(cached => {
            if (cached) return cached;
            return fetch(req).then(resp => {
                if (resp.status === 200) {
                    const copy = resp.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put(req, copy));
                }
                return resp;
            });
        })
    );
});
