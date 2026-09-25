<p align="center"><img src="contrib/32bit/icon.png" width="128" height="128" alt="FastAsyncWorldEdit 32-bit icon"></p>

<h1 align="center">FastAsyncWorldEdit 32-bit</h1>

<p align="center">Fork of FastAsyncWorldEdit 2.15.4 with 32-bit block state ids, for modded servers that have more than 65 536 block states. Built, not yet validated on a live server.</p>

<p align="center">
  <a href="https://github.com/milkycloud-dev/fastasyncworldedit-32bit/actions/workflows/build-32bit.yml"><img src="https://github.com/milkycloud-dev/fastasyncworldedit-32bit/actions/workflows/build-32bit.yml/badge.svg?branch=32bit" alt="Build"></a>
  <a href="https://github.com/milkycloud-dev/fastasyncworldedit-32bit/releases/latest"><img src="https://img.shields.io/github/v/release/milkycloud-dev/fastasyncworldedit-32bit" alt="Release"></a>
  <a href="LICENSE.txt"><img src="https://img.shields.io/badge/license-GPL--3.0-blue" alt="License: GPL-3.0"></a>
</p>

<p align="center"><a href="#english">English</a> | <a href="#русский">Русский</a></p>

<a id="english"></a>

## English

### Overview

FastAsyncWorldEdit keeps every block of an edit as a single `char`: a 16-bit ordinal of the block state. That gives a hard ceiling of 65 536 block states per server. Vanilla 1.21 stays well below that, so the limit is invisible on Paper. A large NeoForge modpack on a Bukkit hybrid core can have far more: the server this fork was made for has about 279 000. Every state above the ceiling reads back as air, and on that modpack FAWE's block registry did not even initialise.

Upstream WorldEdit has no such ceiling. It keys states in a hash map, but it is much slower on big edits. This fork keeps FAWE and widens the type.

### What changed

The full list is in [CHANGES-32bit.md](CHANGES-32bit.md). In short:

- **32-bit ordinals.** `char` is replaced by `int` wherever it means a block state id or the light level stored next to it: 425 replacements in 46 files, done by [contrib/32bit/widen.py](contrib/32bit/widen.py) and finished by `fix2.py` and `fix3.py`.
- **Formats.** The schematic palette used `Character.MAX_VALUE` as the empty slot, which is now a legal id; the marker changed. `DiskOptimizedClipboard` stores 4 bytes per block and bumps its file version to 3, so a buffer written by stock FAWE is never misread.
- **Four bug fixes for modded cores** ([contrib/32bit/hybrid_fixes.py](contrib/32bit/hybrid_fixes.py)):
  1. `generateStateOrdinals` advanced its counter on packing collisions, so ordinals ran past the end of the list and the static initialiser failed for good.
  2. A modded block that throws during registration is now skipped by name instead of breaking the registry.
  3. `BukkitBlockMaterial` no longer constructs block entities while the registry is built, before mod configs are loaded.
  4. `CachedBukkitAdapter` sized its tables by `Material.values().length`. Hybrid cores keep modded materials out of `values()`, while their ordinals go far beyond its length. The tables now grow to the ordinals they see.
- **Build scope.** Only the Minecraft 1.21 adapter is built.

### Status

The jar compiles, and the bytecode was checked for the widened types. It has **not** run on a production server yet. Test it on a copy of your world first, and keep stock FAWE or WorldEdit at hand. Exactly one of them may be installed at a time; WorldGuard depends on it.

### Requirements

- Java 21
- Paper 1.21 or a Paper-based hybrid core (Mohist, Youer, Arclight) for 1.21.1
- Nothing else; the jar bundles what FAWE bundles

### Installation

Download `FastAsyncWorldEdit-32bit-2.15.4.jar` from [Releases](https://github.com/milkycloud-dev/fastasyncworldedit-32bit/releases), remove any other FAWE or WorldEdit jar from `plugins/`, put this one in and restart.

### Building

```bash
./gradlew -Dorg.gradle.configureondemand=false :worldedit-bukkit:shadowJar
```

The build needs the `.git` directory and a few gigabytes of heap. The jar is written to `worldedit-bukkit/build/libs/`. Tags `*-32bit*` are built by GitHub Actions and published as releases.

### Credits and license

FastAsyncWorldEdit is developed by [IntellectualSites](https://github.com/IntellectualSites/FastAsyncWorldEdit) and based on WorldEdit by EngineHub. The upstream README is kept in [README.upstream.md](README.upstream.md). This fork, like the original, is distributed under the [GNU GPL-3.0](LICENSE.txt). It is not affiliated with or endorsed by IntellectualSites.

<a id="русский"></a>

## Русский

### Обзор

FastAsyncWorldEdit хранит каждый блок правки одним `char`: 16-битным номером состояния блока. Отсюда жёсткий потолок в 65 536 состояний на сервер. Ванильная 1.21 до него далеко не дотягивает, поэтому на Paper предела не видно. Большая сборка модов NeoForge на гибридном ядре Bukkit может дать гораздо больше: на сервере, для которого делался форк, их около 279 000. Всё выше потолка читается как воздух, а на этой сборке реестр блоков FAWE даже не инициализировался.

У WorldEdit такого потолка нет, он хранит состояния в хэш-таблице, но на больших правках он намного медленнее. Этот форк оставляет FAWE и расширяет тип.

### Что изменено

Полный список в [CHANGES-32bit.md](CHANGES-32bit.md). Коротко:

- **32-битные номера.** `char` заменён на `int` везде, где он означает номер состояния блока или уровень света рядом с ним: 425 замен в 46 файлах. Их сделал [contrib/32bit/widen.py](contrib/32bit/widen.py), довели `fix2.py` и `fix3.py`.
- **Форматы.** Палитра схематик использовала `Character.MAX_VALUE` как пустую ячейку, а теперь это допустимый номер, так что маркер изменён. `DiskOptimizedClipboard` хранит 4 байта на блок и поднимает версию файла до 3, чтобы буфер обычного FAWE никогда не прочитался неправильно.
- **Четыре исправления для модовых ядер** ([contrib/32bit/hybrid_fixes.py](contrib/32bit/hybrid_fixes.py)):
  1. `generateStateOrdinals` увеличивал счётчик на коллизиях упаковки, номера уходили за конец списка, и статический инициализатор падал насовсем.
  2. Модовый блок, который бросает исключение при регистрации, теперь пропускается поимённо, а не ломает реестр.
  3. `BukkitBlockMaterial` больше не создаёт блок-сущности во время сборки реестра, до загрузки конфигов модов.
  4. `CachedBukkitAdapter` задавал размер таблиц по `Material.values().length`. Гибридные ядра не кладут модовые материалы в `values()`, а их порядковые номера уходят далеко за его длину. Теперь таблицы растут до тех номеров, которые встречаются.
- **Объём сборки.** Собирается только адаптер Minecraft 1.21.

### Статус

Jar собирается, байткод проверен на расширенные типы. На рабочем сервере он **ещё не запускался**. Сначала проверьте его на копии мира и держите под рукой обычный FAWE или WorldEdit. Одновременно может стоять ровно один из них, от него зависит WorldGuard.

### Требования

- Java 21
- Paper 1.21 или гибридное ядро на основе Paper (Mohist, Youer, Arclight) для 1.21.1
- Больше ничего, в jar вшито то же, что вшивает FAWE

### Установка

Скачать `FastAsyncWorldEdit-32bit-2.15.4.jar` из [Releases](https://github.com/milkycloud-dev/fastasyncworldedit-32bit/releases), убрать из `plugins/` любые другие jar FAWE или WorldEdit, положить этот и перезапустить сервер.

### Сборка

```bash
./gradlew -Dorg.gradle.configureondemand=false :worldedit-bukkit:shadowJar
```

Для сборки нужна папка `.git` и несколько гигабайт памяти. Jar появляется в `worldedit-bukkit/build/libs/`. Теги `*-32bit*` собираются в GitHub Actions и публикуются как релизы.

### Авторы и лицензия

FastAsyncWorldEdit разрабатывает [IntellectualSites](https://github.com/IntellectualSites/FastAsyncWorldEdit) на основе WorldEdit от EngineHub. README оригинала сохранён в [README.upstream.md](README.upstream.md). Форк, как и оригинал, распространяется под [GNU GPL-3.0](LICENSE.txt). С IntellectualSites он не связан и ими не одобрен.
