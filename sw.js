const CACHE_NAME = 'astralsurge-os-v5.16';
const APP_SHELL = [
    new URL('./', self.location.href).href,
    new URL('./index.html', self.location.href).href,
    new URL('./index.html?storage=local', self.location.href).href,
    new URL('./standalone.html', self.location.href).href,
    new URL('./manifest.json', self.location.href).href
];
const CACHEABLE_URLS = new Set(APP_SHELL);
const OFFLINE_PAGE = new URL('./index.html', self.location.href).href;

self.addEventListener('install', event => {
    event.waitUntil(caches.open(CACHE_NAME).then(cache => cache.addAll(APP_SHELL)));
});

self.addEventListener('activate', event => {
    event.waitUntil((async () => {
        const keys = await caches.keys();
        await Promise.all(keys
            .filter(key => (key.startsWith('astralsurge-os-') || key.startsWith('aether-os-')) && key !== CACHE_NAME)
            .map(key => caches.delete(key)));
    })());
});

self.addEventListener('fetch', event => {
    const request = event.request;
    const requestUrl = new URL(request.url);
    if (request.method !== 'GET' ||
        requestUrl.origin !== self.location.origin ||
        !CACHEABLE_URLS.has(requestUrl.href)) return;

    event.respondWith((async () => {
        const cached = await caches.match(request);
        if (cached) return cached;

        try {
            const response = await fetch(request);
            if (response.ok && response.type === 'basic') {
                const cache = await caches.open(CACHE_NAME);
                await cache.put(request, response.clone());
            }
            return response;
        } catch (error) {
            if (request.mode === 'navigate') {
                const offlinePage = await caches.match(OFFLINE_PAGE);
                if (offlinePage) return offlinePage;
            }
            throw error;
        }
    })());
});
