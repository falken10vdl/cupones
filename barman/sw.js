/* ============================================================
   sw.js – Service Worker for Barman PWA
   Cache-first for app assets, network-first for /api/ calls
   ============================================================ */

const CACHE_NAME = 'barman-v1';

const APP_ASSETS = [
  '/barman/',
  '/barman/index.html',
  '/barman/app.js',
  '/barman/scanner.js',
  '/barman/offline.js',
  '/barman/manifest.json'
];

// ── Install: pre-cache all app assets ───────────────────────
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      return cache.addAll(APP_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// ── Activate: remove old caches ─────────────────────────────
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys =>
      Promise.all(
        keys
          .filter(key => key !== CACHE_NAME)
          .map(key => caches.delete(key))
      )
    ).then(() => self.clients.claim())
  );
});

// ── Fetch: route requests ────────────────────────────────────
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API calls → network-first, no caching
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(networkFirst(event.request));
    return;
  }

  // App assets → cache-first
  event.respondWith(cacheFirst(event.request));
});

// Cache-first strategy
async function cacheFirst(request) {
  const cached = await caches.match(request);
  if (cached) return cached;

  try {
    const response = await fetch(request);
    if (response.ok) {
      const cache = await caches.open(CACHE_NAME);
      cache.put(request, response.clone());
    }
    return response;
  } catch {
    // Return a basic offline fallback for navigation requests
    if (request.mode === 'navigate') {
      const cached = await caches.match('/barman/index.html');
      if (cached) return cached;
    }
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

// Network-first strategy (no caching)
async function networkFirst(request) {
  try {
    return await fetch(request);
  } catch {
    return new Response(
      JSON.stringify({ error: 'offline', message: 'Sin conexión' }),
      {
        status: 503,
        headers: { 'Content-Type': 'application/json' }
      }
    );
  }
}
