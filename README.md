# iOS / Web
Экспериментальный браузерный порт [Inferno](https://github.com/ChefKissInc/Inferno) (QEMU) и статический интерфейс для GitHub Pages.

**WASM собран и проверен в Chromium:** настоящая ARM64-программа, исполнение кода и доступ к данным выше 4 ГБ, OPFS, IndexedDB, пауза, продолжение и повторный запуск. **Загрузка iOS не подтверждена:** Apple firmware и образы iOS не предоставлены и не включены.

Сайт: https://lakomoor.github.io/ios-web/

## Реализация
- Настоящий движок Inferno, собранный Emscripten, с ARM64 и TCI.
- Виртуальные регистры TCI и гостевые адреса — 64-битные; указатели хоста WASM остаются 32-битными. Кэш TCI ограничен 32 МБ.
- Native QEMU DisplayChangeListener → pixman RGBA → Canvas; абсолютный указатель → QEMU Input.
- Dedicated Web Worker и pthreads; WORKERFS читает выбранные файлы без загрузки на сервер и без полного копирования диска.
- Подкачка гостевой RAM в OPFS с запасным backend IndexedDB: страницы 64 КБ, ограниченный LRU-кэш, отдельный storage worker и синхронный mailbox на SharedArrayBuffer.
- OPFS хранит вытесненные страницы в компактных слотах. Высокий адрес гостевой RAM не создаёт многогигабайтный разреженный файл. Завершённые IndexedDB-сеансы очищаются при следующем запуске; Web Locks защищают активные сеансы других вкладок.
- В режиме подкачки основная RAM представлена MemoryRegionOps. Прямые указатели на вытесняемые страницы не попадают в TLB / DMA. Исполнение из такой памяти использует медленный однократный перевод инструкций QEMU; это значительно медленнее обычного TCI.
- Небольшой framebuffer закреплён в памяти и обслуживается тем же доступом к гостевой RAM.
- Без подкачки максимум гостевой RAM — 1792 МБ. С подкачкой T8030 допускает 4096 МБ при резидентном кэше 64–512 МБ. Остальные буферы эмулятора всё равно расходуют RAM; подкачка не гарантирует запуск конкретной iOS.
- Service worker устанавливает COOP/COEP на статическом хостинге. Все пути относительные, включая /ios-web/ на GitHub Pages.
- Временный snapshot защищает исходный диск от изменений. При остановке изменения теряются. Сохранение состояния iOS, сеть, звук и USB passthrough не реализованы.

## Запуск готовой сборки
Проверенные WASM и диагностические ELF включены в `web/runtime/`. Для обычного запуска Docker не нужен:

```sh
npm ci --ignore-scripts
node scripts/build.mjs --require-runtime
python3 scripts/serve.py --pages
```

Откройте http://localhost:4173/ios-web/. Для другого статического сервера используйте каталог `dist/` и HTTPS. Гостевые файлы выбираются локально в браузере.

## Сборка движка из исходников
Требуются Docker, Git, Node.js и Python 3.

```sh
bash scripts/prepare-source.sh
docker build --secret id=ca,src=/etc/ssl/certs/ca-certificates.crt -t ios-web-builder -f build/Dockerfile .
docker run --rm -v "$PWD:/project" -v /etc/ssl/certs/ca-certificates.crt:/run/build-ca.pem:ro ios-web-builder bash build/compile.sh
npm ci --ignore-scripts
npm test
node scripts/build.mjs --require-runtime
python3 scripts/serve.py --pages
```

Откройте http://localhost:4173/ios-web/. Сервис --pages намеренно не выставляет COOP/COEP: проверяется service worker, как на GitHub Pages. Требуется HTTPS или localhost. Первый заход перезагружает страницу для включения изоляции.

В среде с Docker VFS используйте один изменяемый контейнер, чтобы копирование слоёв не заполнило диск:

```sh
docker run --name ios-web-build -v "$PWD:/project" -v /etc/ssl/certs/ca-certificates.crt:/run/build-ca.pem:ro -w /project emscripten/emsdk:4.0.15 bash build/setup-container.sh
# После исправления ошибки:
docker start ios-web-build
```

## Проверка
Кнопка «Проверить ARM64 без образов» загружает небольшой настоящий ELF64 через загрузчик ядра QEMU. Успех требует строки INFERNO_WASM_ARM64_OK из UART гостя после проверки 64-битной арифметики, записи и чтения RAM. При подкачке код запускается с `0x100080000`, данные проверяются по `0x100090000`; лог содержит ARM64_HIGH_ADDRESS_OK. Гостевая RAM — 4096 МБ, резидентный кэш — 64 МБ.

Перед этим нативный тест вытесняет 256 страниц при кэше на 64 страницы, проверяет возврат страницы по смещению 3 ГБ и доступ через границу страниц. Браузерные тесты отдельно проверяют оба хранилища, компактность OPFS, сохранность активных IndexedDB-сеансов и очистку завершённых.

Этот тест проверяет движок и подкачку; он не доказывает загрузку iOS. Для iOS нужны согласованные kernelcache, DeviceTree, TrustCache, system disk и CHRP NVRAM, подготовленные по [инструкции Inferno](https://chefkiss.dev/applehax/inferno/). IPSW напрямую не запускается.

```sh
node tests/browser.mjs --capture
bash scripts/make-gif.sh
```

`Verify and deploy Pages` проверяет готовый модуль настоящим ARM64-тестом и публикует `dist/`. `Rebuild Inferno from source` отдельно пересобирает движок Docker/Emscripten, повторяет браузерные проверки и сохраняет артефакт `rebuilt-site`. Он запускается при изменении сборочных исходников и вручную из Actions. После изменения C-кода обновите проверенные файлы `web/runtime/`.

## Исходники и лицензии
Upstream закреплён: cc4302a99167abec69b714cfd00c38caece7e7de. Изменения воспроизводятся через build/patch.py; оригинальный исходный код загружается scripts/prepare-source.sh. Новые файлы — AGPL-3.0-only, компоненты Inferno и зависимости сохраняют собственные GPL/AGPL/LGPL и другие лицензии. Проект независим от Apple, ChefKiss и QEMU.
