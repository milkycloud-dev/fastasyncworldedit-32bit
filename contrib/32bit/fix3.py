"""Третья волна.

1) Векторный путь живёт ещё в трёх фильтрах вне пакета simd: доводим и их.

2) DiskOptimizedClipboard: единственное место, где расширение не сводится
   к смене типа: это дисковый формат. Блок занимал два байта, теперь четыре.
   Значит:
     - смещения блоков считаются как index << 2 вместо index << 1;
     - чтение и запись идут через getInt/putInt вместо getChar/putChar;
     - поля заголовка (версия, размеры, счётчики) остаются двухбайтовыми,
       им расширение ни к чему: возвращаем им (char);
     - версия формата поднимается с 2 до 3, чтобы старый файл нельзя было
       прочитать новым кодом как свой.
   Это временные файлы буфера обмена FAWE, а не схематики игроков: после
   смены версии они просто пересоздаются.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CORE = "worldedit-core/src/main/java/"

SIMD_RULES = [
    ("jdk.incubator.vector.ShortVector", "jdk.incubator.vector.IntVector"),
    ("ShortVector", "IntVector"),
    ("VectorSpecies<Short>", "VectorSpecies<Integer>"),
    ("VectorMask<Short>", "VectorMask<Integer>"),
    ("fromCharArray", "fromArray"),
    ("intoCharArray", "intoArray"),
    ("(short) ", ""),
]

SIMD_FILES = [
    CORE + "com/fastasyncworldedit/core/extent/filter/MaskFilter.java",
    CORE + "com/fastasyncworldedit/core/extent/filter/LinkedFilter.java",
    CORE + "com/fastasyncworldedit/core/extent/filter/CountFilter.java",
]

DOC = CORE + "com/fastasyncworldedit/core/extent/clipboard/DiskOptimizedClipboard.java"

DOC_RULES = [
    # версия формата
    ("    public static final int VERSION = 2;", "    public static final int VERSION = 3;"),
    # заголовок остаётся двухбайтовым
    ("byteBuffer.putChar(2, (int) (VERSION));", "byteBuffer.putChar(2, (char) (VERSION));"),
    ("byteBuffer.putChar(4, (int) getWidth());", "byteBuffer.putChar(4, (char) getWidth());"),
    ("byteBuffer.putChar(6, (int) getHeight());", "byteBuffer.putChar(6, (char) getHeight());"),
    ("byteBuffer.putChar(8, (int) getLength());", "byteBuffer.putChar(8, (char) getLength());"),
    ("byteBuffer.putChar(23, (int) count);", "byteBuffer.putChar(23, (char) count);"),
    ("byteBuffer.putChar(25, (int) count);", "byteBuffer.putChar(25, (char) count);"),
    # блок занимает четыре байта
    ("(long) getVolume() << 1", "(long) getVolume() << 2"),
    ("(getVolume() << 1)", "(getVolume() << 2)"),
    ("(index << 1)", "(index << 2)"),
    ("(getIndex(x, y, z) << 1)", "(getIndex(x, y, z) << 2)"),
    ("(i << 1)", "(i << 2)"),
    # чтение и запись номера блока
    ("byteBuffer.getChar(diskIndex)", "byteBuffer.getInt(diskIndex)"),
    ("byteBuffer.putChar(index, ordinal)", "byteBuffer.putInt(index, ordinal)"),
]


def main():
    print("=== векторный путь в фильтрах ===")
    for f in SIMD_FILES:
        p = os.path.join(ROOT, f)
        t = open(p, encoding="utf-8").read()
        before = t
        for old, new in SIMD_RULES:
            t = t.replace(old, new)
        if t != before:
            open(p, "w", encoding="utf-8").write(t)
            print("   %-50s правлен" % f.split("/")[-1])
        else:
            print("   %-50s без изменений" % f.split("/")[-1])

    print()
    print("=== дисковый буфер обмена ===")
    p = os.path.join(ROOT, DOC)
    t = open(p, encoding="utf-8").read()
    for old, new in DOC_RULES:
        n = t.count(old)
        if n == 0:
            print("   пропуск (уже применено или не найдено): %s" % old[:60])
            continue
        t = t.replace(old, new)
        print("   %-58s x%d" % (old[:58], n))
    open(p, "w", encoding="utf-8").write(t)


if __name__ == "__main__":
    main()
