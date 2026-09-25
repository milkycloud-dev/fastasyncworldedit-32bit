"""Вторая волна: чинит то, на что ругнулся компилятор после расширения типа.

Пять групп:
  1) файлы, которые я не включил в первый список, а зря: там тоже номера блоков;
  2) перегрузки, ставшие одинаковыми после расширения (toRaw, toPalette);
  3) обёртка Character в коллекциях -> Integer;
  4) fastutil-карты с ключом char -> с ключом int;
  5) векторный путь (SIMD): ShortVector -> IntVector.

Отдельно важное: сторожевое значение Character.MAX_VALUE (65535) после
расширения стало обычным номером блока. Меняем на Integer.MAX_VALUE, иначе
блок с номером 65535 будет считаться пустой ячейкой палитры.
"""
import os
import re
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CORE = "worldedit-core/src/main/java/"
TYPE = re.compile(r"\bchar\b")

# --- 1. дозаливка: тут char тоже означает номер блока -------------------------
EXTRA_BLANKET = [
    CORE + "com/sk89q/worldedit/regions/Region.java",
    CORE + "com/sk89q/worldedit/regions/CuboidRegion.java",
    CORE + "com/sk89q/worldedit/math/BlockVector3.java",
    CORE + "com/fastasyncworldedit/core/math/DelegateBlockVector3.java",
    CORE + "com/fastasyncworldedit/core/util/TextureUtil.java",
    CORE + "com/fastasyncworldedit/core/util/RandomTextureUtil.java",
    CORE + "com/fastasyncworldedit/core/util/DelegateTextureUtil.java",
    CORE + "com/fastasyncworldedit/core/extent/clipboard/io/schematic/MinecraftStructure.java",
]

# --- 2..5 точечные правки ------------------------------------------------------
FIXES = {
    # Две одинаковые перегрузки: одна была char[], другая int[]. Тела совпадают
    # (обе читают ordinal по абсолютному индексу), поэтому вторую просто
    # переименовываем: удалять кусок текста рискованнее.
    CORE + "com/fastasyncworldedit/core/math/BitArray.java": [
        ("SECOND", "    public int[] toRaw(int[] buffer) {", "    public int[] toRawLegacy(int[] buffer) {"),
    ],
    CORE + "com/fastasyncworldedit/core/math/BitArrayUnstretched.java": [
        ("SECOND", "    public int[] toRaw(int[] buffer) {", "    public int[] toRawLegacy(int[] buffer) {"),
    ],
    CORE + "com/fastasyncworldedit/core/FaweCache.java": [
        ("ONCE", "    public Palette toPalette(int layerOffset, int[] blocks) {\n        return toPalette(layerOffset, blocks, null);\n    }",
         "    public Palette toPaletteFromInts(int layerOffset, int[] blocks) {\n        return toPalette(layerOffset, blocks, null);\n    }"),
    ],
    CORE + "com/fastasyncworldedit/core/extent/processor/PlacementStateProcessor.java": [
        ("ALL", "Character", "Integer"),
    ],
    CORE + "com/fastasyncworldedit/core/extent/clipboard/io/schematic/MinecraftStructure.java": [
        ("ALL", "it.unimi.dsi.fastutil.chars.Char2IntArrayMap", "it.unimi.dsi.fastutil.ints.Int2IntArrayMap"),
        ("ALL", "it.unimi.dsi.fastutil.chars.Char2IntMap", "it.unimi.dsi.fastutil.ints.Int2IntMap"),
        ("ALL", "Char2IntMap", "Int2IntMap"),
        ("ALL", "Char2IntArrayMap", "Int2IntArrayMap"),
    ],
    CORE + "com/fastasyncworldedit/core/extent/clipboard/io/FastSchematicWriterV3.java": [
        ("ALL", "Function<T, Character> ordinalResolver", "Function<T, Integer> ordinalResolver"),
        ("ALL", "Character.MAX_VALUE", "Integer.MAX_VALUE"),
    ],
    CORE + "com/fastasyncworldedit/core/extent/clipboard/io/FastSchematicWriterV2.java": [
        ("ALL", "Character.MAX_VALUE", "Integer.MAX_VALUE"),
    ],
    CORE + "com/fastasyncworldedit/core/extent/clipboard/io/FastSchematicReaderV3.java": [
        ("ALL", "Character.MAX_VALUE", "Integer.MAX_VALUE"),
    ],
}

# --- 5. векторный путь ---------------------------------------------------------
SIMD_DIR = CORE + "com/fastasyncworldedit/core/internal/simd/"
SIMD_RULES = [
    ("jdk.incubator.vector.ShortVector", "jdk.incubator.vector.IntVector"),
    ("ShortVector", "IntVector"),
    ("VectorSpecies<Short>", "VectorSpecies<Integer>"),
    ("VectorMask<Short>", "VectorMask<Integer>"),
    ("fromCharArray", "fromArray"),
    ("intoCharArray", "intoArray"),
    ("(short) ", ""),
]


def apply_second(text, old, new):
    first = text.find(old)
    if first < 0:
        raise SystemExit("не найден якорь: %r" % old[:60])
    second = text.find(old, first + len(old))
    if second < 0:
        raise SystemExit("второго вхождения нет: %r" % old[:60])
    return text[:second] + new + text[second + len(old):]


def main():
    print("=== дозаливка расширения ===")
    for f in EXTRA_BLANKET:
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            print("   нет файла:", f)
            continue
        t = open(p, encoding="utf-8").read()
        n = len(TYPE.findall(t))
        if n:
            open(p, "w", encoding="utf-8").write(TYPE.sub("int", t))
        print("   %-72s %2d" % (f.split("/java/")[-1], n))

    print()
    print("=== точечные правки ===")
    for f, rules in FIXES.items():
        p = os.path.join(ROOT, f)
        t = open(p, encoding="utf-8").read()
        for kind, old, new in rules:
            if kind in ("SECOND", "ONCE"):
                marker = new.strip().split("(")[0].split()[-1]
                if marker in t:
                    print("   %-60s уже применено (%s)" % (f.split("/java/")[-1], marker))
                    continue
                t = apply_second(t, old, new) if kind == "SECOND" else t.replace(old, new, 1)
                print("   %-60s -> %s" % (f.split("/java/")[-1], marker))
            else:
                n = t.count(old)
                t = t.replace(old, new)
                print("   %-60s %s -> %s (%d)" % (f.split("/java/")[-1], old[:34], new[:28], n))
        open(p, "w", encoding="utf-8").write(t)

    print()
    print("=== векторный путь ===")
    d = os.path.join(ROOT, SIMD_DIR)
    for name in sorted(os.listdir(d)):
        if not name.endswith(".java"):
            continue
        p = os.path.join(d, name)
        t = open(p, encoding="utf-8").read()
        before = t
        for old, new in SIMD_RULES:
            t = t.replace(old, new)
        if t != before:
            open(p, "w", encoding="utf-8").write(t)
            print("   %-40s правлен" % name)


if __name__ == "__main__":
    main()
