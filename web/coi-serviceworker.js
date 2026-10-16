// SPDX-License-Identifier: MIT
// COOP/COEP for static hosts, including project-scoped GitHub Pages.
self.addEventListener('install', () => self.skipWaiting());
self.addEventListener('activate', event => event.waitUntil(self.clients.claim()));
self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.cache === 'only-if-cached' && req.mode !== 'same-origin') return;
  event.respondWith((async () => {
    const response = await fetch(req);
    if (response.status === 0) return response;
    const headers = new Headers(response.headers);
    headers.set('Cross-Origin-Opener-Policy','same-origin');
    headers.set('Cross-Origin-Embedder-Policy','require-corp');
    headers.set('Cross-Origin-Resource-Policy','same-origin');
    return new Response(response.body, {status:response.status,statusText:response.statusText,headers});
  })());
});
