export async function ensureIsolation() {
  if (globalThis.crossOriginIsolated) return true;
  if (!globalThis.isSecureContext) throw new Error('Откройте сайт через HTTPS или localhost.');
  if (!('serviceWorker' in navigator)) throw new Error('Браузер не поддерживает service worker. Нужен современный Chrome, Firefox или Safari.');
  await navigator.serviceWorker.register(new URL('./coi-serviceworker.js', import.meta.url), {scope:'./', updateViaCache:'none'});
  await navigator.serviceWorker.ready;
  if (!navigator.serviceWorker.controller) {
    await new Promise((resolve,reject) => {
      const timer = setTimeout(() => reject(new Error('Service worker не получил управление. Перезагрузите страницу.')), 15000);
      navigator.serviceWorker.addEventListener('controllerchange', () => {clearTimeout(timer);resolve();}, {once:true});
    });
  }
  const key = 'ios-web-isolation-reload';
  if (sessionStorage.getItem(key) === location.href) throw new Error('Не удалось включить изоляцию. Откройте сайт в отдельной вкладке и разрешите service worker.');
  sessionStorage.setItem(key,location.href);
  location.reload();
  return false;
}
