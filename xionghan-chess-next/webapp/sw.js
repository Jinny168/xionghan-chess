/* 极简离线缓存：应用外壳优先，网络失败时回退缓存。 */
const CACHE = 'xh-web-v1';
const ASSETS = [
  './',
  './index.html',
  './css/app.css',
  './js/i18n.js',
  './js/ai-worker.js',
  './js/core/model.js',
  './js/core/profiles.js',
  './js/core/rules.js',
  './js/core/game.js',
  './js/core/movegen.js',
  './js/core/ai.js',
  './js/ui/board.js',
  './js/ui/sound.js',
  './js/ui/app.js',
  './manifest.webmanifest',
  './favicon.svg',
];

self.addEventListener('install', (event) => {
  event.waitUntil(caches.open(CACHE).then((cache) => cache.addAll(ASSETS)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))))
      .then(() => self.clients.claim()),
  );
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return;
  event.respondWith(
    caches.match(request).then((cached) => cached || fetch(request).then((response) => {
      const copy = response.clone();
      caches.open(CACHE).then((cache) => cache.put(request, copy)).catch(() => {});
      return response;
    }).catch(() => caches.match('./index.html'))),
  );
});
