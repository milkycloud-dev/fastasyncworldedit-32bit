"""Расширяет номер состояния блока в FAWE с 16 бит (char) до 32 (int).

Зачем: FAWE хранит каждый блок мира одним char. Потолок: 65536 состояний
блоков на сервер. В модовой сборке, под которую делался форк, их около 279 тысяч, и без этой
правки 456 блоков просто не помещаются в реестр, а читаются как воздух.

Как: в файлах, где char означает именно номер состояния блока (и заодно
уровень света, лежащий в тех же массивах), тип меняется на int. Регулярное
выражение \\bchar\\b не задевает ни имена классов (CharBlocks), ни методы
(charAt), ни Character.MAX_VALUE: только сам тип.

Файлы, где char означает символ текста, правятся поимённо и точечно.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CORE = "worldedit-core/src/main/java/"
BUKKIT = "worldedit-bukkit/src/main/java/"
ADAPTER = "worldedit-bukkit/adapters/adapter-1_21/src/main/java/"

# Каталоги, где char означает номер состояния блока целиком.
BLANKET_DIRS = [
    CORE + "com/fastasyncworldedit/core/queue/",
    CORE + "com/fastasyncworldedit/core/extent/filter/block/",
    CORE + "com/fastasyncworldedit/core/extent/clipboard/",
    CORE + "com/fastasyncworldedit/core/history/",
    CORE + "com/fastasyncworldedit/core/internal/simd/",
    CORE + "com/fastasyncworldedit/core/extent/processor/heightmap/",
    BUKKIT + "com/fastasyncworldedit/bukkit/adapter/",
    ADAPTER,
]

BLANKET_FILES = [
    CORE + "com/fastasyncworldedit/core/FaweCache.java",
    CORE + "com/fastasyncworldedit/core/extent/processor/PlacementStateProcessor.java",
    CORE + "com/fastasyncworldedit/core/math/BitArray.java",
    CORE + "com/fastasyncworldedit/core/math/BitArrayUnstretched.java",
    CORE + "com/fastasyncworldedit/core/extent/DisallowedBlocksExtent.java",
    CORE + "com/fastasyncworldedit/core/function/mask/SingleBlockStateMask.java",
    CORE + "com/fastasyncworldedit/core/math/heightmap/ScalableHeightMap.java",
    CORE + "com/fastasyncworldedit/core/math/heightmap/ArrayHeightMap.java",
    CORE + "com/sk89q/worldedit/function/mask/InverseSingleBlockStateMask.java",
    CORE + "com/sk89q/worldedit/world/block/BlockStateHolder.java",
    CORE + "com/sk89q/worldedit/world/block/BaseBlock.java",
]

# Файлы, где char встречается и как символ текста: правим адресно.
SELECTIVE = {
    CORE + "com/sk89q/worldedit/world/block/BlockState.java": [
        ("    private final char ordinalChar;", "    private final int ordinalChar;", 1),
        ("        this.ordinalChar = (char) ordinal;", "        this.ordinalChar = ordinal;", 2),
        ("    public final char getOrdinalChar() {", "    public final int getOrdinalChar() {", 1),
    ],
}

SKIP_NAMES = {"StringMan.java", "StringUtil.java", "MutableCharSequence.java",
              "JoinedCharSequence.java", "CommandContext.java", "CommandsManager.java",
              "JSON2NBT.java", "YAMLProcessor.java", "MemorySection.java",
              "ConfigurationOptions.java", "MemoryConfigurationOptions.java",
              "FileConfigurationOptions.java", "YamlConfigurationOptions.java",
              "LevenshteinDistance.java", "SuggestionHelper.java", "DataReport.java",
              "Identifiable.java", "SchemVis.java"}

TYPE = re.compile(r"\bchar\b")


def blanket(path):
    text = open(path, encoding="utf-8").read()
    hits = len(TYPE.findall(text))
    if not hits:
        return 0
    open(path, "w", encoding="utf-8").write(TYPE.sub("int", text))
    return hits


def main():
    total = 0
    touched = 0
    for d in BLANKET_DIRS:
        full = os.path.join(ROOT, d)
        if not os.path.isdir(full):
            print("  нет каталога:", d)
            continue
        for dp, _, fn in os.walk(full):
            for f in sorted(fn):
                if not f.endswith(".java") or f in SKIP_NAMES:
                    continue
                n = blanket(os.path.join(dp, f))
                if n:
                    touched += 1
                    total += n
                    print("  %-70s %3d" % (os.path.join(dp, f)[len(ROOT):].lstrip("/\\").replace("\\", "/"), n))

    for f in BLANKET_FILES:
        full = os.path.join(ROOT, f)
        if not os.path.isfile(full):
            print("  нет файла:", f)
            continue
        n = blanket(full)
        if n:
            touched += 1
            total += n
            print("  %-70s %3d" % (f, n))

    print()
    print("=== точечные правки ===")
    for f, rules in SELECTIVE.items():
        full = os.path.join(ROOT, f)
        text = open(full, encoding="utf-8").read()
        for old, new, count in rules:
            got = text.count(old)
            if got != count:
                raise SystemExit("в %s якорь встречается %d раз, ждали %d: %s" % (f, got, count, old))
            text = text.replace(old, new)
            total += count
        open(full, "w", encoding="utf-8").write(text)
        touched += 1
        print("  %-70s %3d" % (f, sum(r[2] for r in rules)))

    print()
    print("файлов изменено:", touched, " замен:", total)


if __name__ == "__main__":
    main()
