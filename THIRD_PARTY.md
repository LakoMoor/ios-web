# Компоненты

Собранный модуль содержит свободные компоненты со своими лицензиями. Новые файлы порта имеют SPDX `AGPL-3.0-only`; исходные заголовки авторских прав Inferno сохранены патчами.

| Компонент | Версия / источник | Лицензия |
| --- | --- | --- |
| Inferno / QEMU | [cc4302a99167abec69b714cfd00c38caece7e7de](https://github.com/ChefKissInc/Inferno/tree/cc4302a99167abec69b714cfd00c38caece7e7de) | AGPL-3.0 / GPL-2.0-or-later и лицензии отдельных файлов |
| GLib | [2.75.0](https://download.gnome.org/sources/glib/2.75/) | LGPL-2.1-or-later |
| libffi | [3.4.8](https://github.com/libffi/libffi/tree/v3.4.8) | MIT |
| pixman | [0.42.2](https://cairographics.org/releases/) | MIT |
| zlib | [1.3.1](https://zlib.net/fossils/) | zlib |
| GMP | [6.3.0](https://gmplib.org/) | LGPL-3.0-or-later / GPL-2.0-or-later |
| Nettle | [3.10.2](https://www.lysator.liu.se/~nisse/nettle/) | LGPL-3.0-or-later / GPL-2.0-or-later |
| libtasn1 | [4.20.0](https://www.gnu.org/software/libtasn1/) | LGPL-2.1-or-later |
| LZFSE | [1.0](https://github.com/lzfse/lzfse/tree/lzfse-1.0) | BSD-3-Clause |
| libpng | [1.6.50](https://libpng.org/) | PNG Reference Library License |
| PCRE2 / gvdb | Закреплены subproject-описаниями GLib | BSD / LGPL |
| libfdt | Закреплён subproject-описанием Inferno | BSD-2-Clause / GPL-2.0-or-later |
| M*LIB | Закреплён submodule-описанием Inferno | BSD-2-Clause |
| Emscripten runtime / musl / LLVM runtime | [Emscripten SDK 4.0.15](https://github.com/emscripten-core/emsdk/tree/4.0.15) | MIT и лицензии соответствующих runtime-компонентов |

Полные исходники Inferno доступны по закреплённой ссылке. Все изменения порта находятся в `build/patch.py` и `build/*.[ch]`; исходники диагностической программы — `build/probe.S`. `scripts/prepare-source.sh` загружает точный upstream вместе с M*LIB. `build/dependencies.sh` загружает версии зависимостей и воспроизводит необходимые изменения GLib. Команды пересборки приведены в README.

Тексты лицензий и уведомления об авторских правах сохранены без изменений в `third_party/` и включены в статическую сборку.
