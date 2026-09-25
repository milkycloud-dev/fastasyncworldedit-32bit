"""Переносит в форк четыре исправления, найденные на живом сервере.

Расширение типа снимает потолок в 65536 состояний, но не чинит сами баги:

1) generateStateOrdinals: счётчик порядковых номеров рос и на коллизии
   упаковки, хотя состояние в список не добавлялось. Номера уезжали за конец
   списка, статический инициализатор падал и убивал весь блочный реестр.

2) Состояние по умолчанию бралось без проверки границ.

3) Один сбойный модовый блок ронял регистрацию целиком. Теперь пропускается
   поимённо, с откатом уже добавленных состояний.

4) BukkitBlockMaterial дёргал конструктор блок-сущности прямо при сборке
   реестра, до загрузки конфигов модов. Теперь лениво, с повторами.

5) CachedBukkitAdapter строил таблицу «Material -> тип» по длине
   Material.values(). На гибридном ядре модовые материалы в этот массив не
   попадают вовсе, а их ordinal уходит далеко за его длину. Теперь таблица
   растёт по факту и заполняется лениво.

Бюджета в 65536 состояний здесь нет: он был вынужденной мерой при char.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = sys.argv[1] if len(sys.argv) > 1 else "."
CORE = "worldedit-core/src/main/java/"
BUKKIT = "worldedit-bukkit/src/main/java/"

BTC = CORE + "com/sk89q/worldedit/world/block/BlockTypesCache.java"
BBM = BUKKIT + "com/fastasyncworldedit/bukkit/adapter/BukkitBlockMaterial.java"
CBA = BUKKIT + "com/fastasyncworldedit/bukkit/adapter/CachedBukkitAdapter.java"

PATCHES = []


def swap(path, old, new, count=1):
    PATCHES.append((path, old, new, count))


# ---------------------------------------------------------------- BlockTypesCache

swap(BTC, """    protected static final Set<String> $NAMESPACES = new LinkedHashSet<>();
""", """    protected static final Set<String> $NAMESPACES = new LinkedHashSet<>();

    // 32-bit fork: блоки, у которых упаковка состояний не сошлась, и блоки,
    // которые ядро вообще не дало зарегистрировать. Списки обрезаны, счётчики
    // отдельно: иначе одна строка лога вырастет на сотни килобайт.
    static final List<String> $PACKING_LOSSES = new ArrayList<>();
    static final List<String> $SKIPPED = new ArrayList<>();
    static int $PACKING_LOSS_COUNT;
    static int $SKIPPED_COUNT;
    static int $TAKEN;
    static int $PLATFORM_STATES;
    static int $LAST_EXPECTED = 1;

    static void notePackingLoss(String id, int expected, int actual) {
        $PACKING_LOSS_COUNT++;
        if ($PACKING_LOSSES.size() < 32) {
            $PACKING_LOSSES.add(id + " (" + actual + " из " + expected + ")");
        }
    }

    static void noteSkipped(String id, Throwable why) {
        $SKIPPED_COUNT++;
        if ($SKIPPED.size() < 32) {
            $SKIPPED.add(id + " (" + why + ")");
        }
    }
""")

swap(BTC, """            // Map it to the ordinal
            result[stateId >> BIT_OFFSET] = ordinal++;
""", """            // Map it to the ordinal
            // 32-bit fork: у модовых блоков две разные перестановки свойств умеют
            // упаковаться в один индекс. Раньше счётчик рос и на такой коллизии,
            // хотя состояние в список не добавлялось, и номера уходили за конец
            // списка. Теперь номер выдаётся только вместе с реальным состоянием.
            int slot = stateId >> BIT_OFFSET;
            if (slot >= 0 && slot < result.length && result[slot] == -1) {
                result[slot] = ordinal++;
            }
""")

swap(BTC, """        int[] result = new int[maxStateId];
        Arrays.fill(result, -1);
""", """        int[] result = new int[Math.max(1, maxStateId)];
        Arrays.fill(result, -1);
""")

swap(BTC, """                int defaultPropId = parseProperties(propertyString, propertiesMap) >> BIT_OFFSET;

                this.defaultState = states.get(this.stateOrdinals[defaultPropId]);
""", """                int defaultPropId = parseProperties(propertyString, propertiesMap) >> BIT_OFFSET;

                // 32-bit fork: сколько перестановок реально легло в таблицу.
                int expected = 1;
                for (AbstractProperty<?> property : propertiesList) {
                    expected *= property.getValues().size();
                }
                $LAST_EXPECTED = expected;
                int actual = 0;
                int firstOrdinal = -1;
                for (int ord : this.stateOrdinals) {
                    if (ord != -1) {
                        actual++;
                        if (firstOrdinal == -1) {
                            firstOrdinal = ord;
                        }
                    }
                }
                if (actual != expected) {
                    notePackingLoss(id, expected, actual);
                }

                int defaultOrdinal = -1;
                if (defaultPropId >= 0 && defaultPropId < this.stateOrdinals.length) {
                    defaultOrdinal = this.stateOrdinals[defaultPropId];
                }
                if (defaultOrdinal < 0 || defaultOrdinal >= states.size()) {
                    defaultOrdinal = firstOrdinal;
                }
                if (defaultOrdinal < 0 || defaultOrdinal >= states.size()) {
                    CompoundTag onlyNBT = blockMaterial.getDefaultTile();
                    BlockState only = onlyNBT != null
                            ? new BlockState(type, internalId, states.size(), onlyNBT)
                            : new BlockState(type, internalId, states.size());
                    this.stateOrdinals[0] = states.size();
                    defaultOrdinal = states.size();
                    states.add(only);
                    notePackingLoss(id, expected, 0);
                }
                this.defaultState = states.get(defaultOrdinal);
""")

swap(BTC, """            } else {
                CompoundTag defaultNBT = blockMaterial.getDefaultTile();
                this.defaultState = defaultNBT != null ? new BlockState(
""", """            } else {
                $LAST_EXPECTED = 1;
                CompoundTag defaultNBT = blockMaterial.getDefaultTile();
                this.defaultState = defaultNBT != null ? new BlockState(
""")

swap(BTC, """                    BlockType type = register(defaultState, internalId, stateList, tickList);
                    values[internalId] = type;
""", """                    // 32-bit fork: раньше любой модовый блок, на котором спотыкался
                    // конструктор, ронял весь статический инициализатор, а с ним
                    // и блочный реестр до конца жизни процесса. Теперь такой блок
                    // пропускается поимённо, уже добавленные состояния откатываются.
                    int stateMark = stateList.size();
                    int tickMark = tickList.size();
                    try {
                        BlockType type = register(defaultState, internalId, stateList, tickList);
                        values[internalId] = type;
                        $TAKEN++;
                        $PLATFORM_STATES += $LAST_EXPECTED;
                    } catch (Throwable badBlock) {
                        while (stateList.size() > stateMark) {
                            stateList.remove(stateList.size() - 1);
                        }
                        while (tickList.size() > tickMark) {
                            tickList.remove(tickList.size() - 1);
                        }
                        noteSkipped(entry.getKey(), badBlock);
                    }
""")

swap(BTC, """            states = stateList.toArray(new BlockState[stateList.size()]);
            ticking = Booleans.toArray(tickList);
""", """            // 32-bit fork: адаптер строит таблицу перевода длиной states.length, а
            // индексирует её идентификатором состояния блока из ядра. Их больше,
            // чем состояний у нас: часть блоков ядро считает по-своему, часть мы
            // не смогли разобрать. Дополняем список ссылками на воздух: лишние
            // ячейки ни на что не указывают, но длина получается с запасом.
            int usedStates = stateList.size();
            if (!stateList.isEmpty()) {
                BlockState filler = stateList.get(0);
                int target = Math.max($PLATFORM_STATES + 65536, 1 << 19);
                while (stateList.size() < target) {
                    stateList.add(filler);
                    tickList.add(Boolean.FALSE);
                }
            }

            states = stateList.toArray(new BlockState[stateList.size()]);
            ticking = Booleans.toArray(tickList);

            java.util.logging.Logger.getLogger("FastAsyncWorldEdit").info(
                    "Блоков у ядра: " + blockMap.size() + ", взято: " + $TAKEN
                            + ", не разобрано: " + $SKIPPED_COUNT
                            + ". Состояний " + usedStates
                            + ", длина таблицы " + states.length
                            + " (потолка в 16 бит больше нет)");
            if (!$SKIPPED.isEmpty()) {
                java.util.logging.Logger.getLogger("FastAsyncWorldEdit").warning(
                        "Не удалось зарегистрировать блоков: " + $SKIPPED_COUNT
                                + ", WorldEdit их не увидит: " + String.join(", ", $SKIPPED));
            }
            if (!$PACKING_LOSSES.isEmpty()) {
                java.util.logging.Logger.getLogger("FastAsyncWorldEdit").warning(
                        "Упаковка состояний не сошлась у " + $PACKING_LOSS_COUNT
                                + " блоков, часть их состояний склеена: "
                                + String.join(", ", $PACKING_LOSSES));
            }
""")

# ------------------------------------------------------------ BukkitBlockMaterial

swap(BBM, """    private final FaweCompoundTag tile;
""", """    // 32-bit fork: раньше значение считалось в конструкторе. Конструктор
    // блок-сущности модового блока умеет полезть в конфиг своего мода, который
    // при сборке реестра ещё не загружен, и тогда наружу летело
    // IllegalStateException: Cannot get config value before config is loaded,
    // убивая весь блочный реестр. Теперь лениво и с повторами.
    private volatile FaweCompoundTag tile;
    private volatile boolean tileResolved;
    private int tileAttempts;
    private static int tileFailuresLogged;
""")

swap(BBM, """        this.craftMaterial = this.blockData.getMaterial();
        this.tile = tileForBlock(block);
    }
""", """        this.craftMaterial = this.blockData.getMaterial();
    }

    private FaweCompoundTag tile() {
        return this.tileResolved ? this.tile : resolveTile();
    }

    private synchronized FaweCompoundTag resolveTile() {
        if (this.tileResolved) {
            return this.tile;
        }
        try {
            this.tile = tileForBlock(this.block);
            this.tileResolved = true;
        } catch (Throwable notReadyYet) {
            this.tile = null;
            if (++this.tileAttempts >= 3) {
                this.tileResolved = true;
                if (tileFailuresLogged < 20) {
                    tileFailuresLogged++;
                    java.util.logging.Logger.getLogger("FastAsyncWorldEdit").warning(
                            "Блок " + this.craftMaterial.getKey()
                                    + ": данные блок-сущности недоступны (" + notReadyYet
                                    + "), блок считается без NBT");
                }
            }
        }
        return this.tile;
    }
""")

swap(BBM, """    public @Nullable FaweCompoundTag defaultTile() {
        return this.tile;
    }
""", """    public @Nullable FaweCompoundTag defaultTile() {
        return tile();
    }
""")

swap(BBM, """    public boolean hasContainer() {
        return this.tile != null;
    }
""", """    public boolean hasContainer() {
        return tile() != null;
    }
""")

swap(BBM, """    public boolean isTile() {
        return this.tile != null;
    }
""", """    public boolean isTile() {
        return tile() != null;
    }
""")

# ------------------------------------------------------------ CachedBukkitAdapter

swap(CBA, """import java.util.List;
""", """import java.util.Arrays;
import java.util.List;
""")

swap(CBA, """    private int[] itemTypes;
    private int[] blockTypes;

    private boolean init() {
        if (itemTypes == null) {
            Material[] materials = Material.values();
            itemTypes = new int[materials.length];
            blockTypes = new int[materials.length];
            for (int i = 0; i < materials.length; i++) {
                Material material = materials[i];
                if (material.isLegacy()) {
                    continue;
                }
                NamespacedKey key = material.getKey();
                String id = key.getNamespace() + ":" + key.getKey();
                if (material.isBlock()) {
                    blockTypes[i] = BlockTypes.get(id).getInternalId();
                }
                if (material.isItem()) {
                    itemTypes[i] = ItemTypes.get(id).getInternalId();
                }
            }
            return true;
        }
        return false;
    }

    /**
     * Converts a Material to a ItemType.
     *
     * @param material The material
     * @return The itemtype
     */
    @Override
    public ItemType asItemType(Material material) {
        try {
            return ItemTypes.get(itemTypes[material.ordinal()]);
        } catch (NullPointerException e) {
            if (init()) {
                return asItemType(material);
            }
            return ItemTypes.get(itemTypes[material.ordinal()]);
        }
    }

    @Override
    public BlockType asBlockType(Material material) {
        try {
            return BlockTypesCache.values[blockTypes[material.ordinal()]];
        } catch (NullPointerException e) {
            if (init()) {
                return asBlockType(material);
            }
            throw e;
        }
    }
""", """    // 32-bit fork: раньше обе таблицы делались один раз по длине Material.values()
    // и индексировались по Material.ordinal(). На гибридном ядре это неверно
    // дважды: модовые материалы добавляются позже, а их ordinal вообще выходит
    // за длину values(): ядро отдаёт около 1500 значений, а ordinal доходит до
    // пяти тысяч с лишним. Теперь таблицы растут по факту и заполняются лениво.
    private static final int UNRESOLVED = -1;

    private volatile int[] itemTypes;
    private volatile int[] blockTypes;

    private synchronized int[] grow(boolean items, int ordinal) {
        int[] current = items ? itemTypes : blockTypes;
        if (current != null && ordinal < current.length) {
            return current;
        }
        int size = Math.max(ordinal + 1, Material.values().length);
        if (current != null) {
            size = Math.max(size, current.length * 2);
        }
        int[] grown = new int[size];
        Arrays.fill(grown, UNRESOLVED);
        if (current != null) {
            System.arraycopy(current, 0, grown, 0, current.length);
        }
        if (items) {
            itemTypes = grown;
        } else {
            blockTypes = grown;
        }
        return grown;
    }

    /** Внутренний номер типа, либо UNRESOLVED: тогда значение не кэшируется. */
    private int resolve(Material material, boolean items) {
        try {
            if (material.isLegacy()) {
                return 0;
            }
            NamespacedKey key = material.getKey();
            String id = key.getNamespace() + ":" + key.getKey();
            if (items) {
                ItemType type = ItemTypes.get(id);
                return type == null ? UNRESOLVED : type.getInternalId();
            }
            BlockType type = BlockTypes.get(id);
            return type == null ? UNRESOLVED : type.getInternalId();
        } catch (Throwable broken) {
            return 0;
        }
    }

    private int itemId(Material material) {
        int ordinal = material.ordinal();
        int[] table = itemTypes;
        if (table == null || ordinal >= table.length) {
            table = grow(true, ordinal);
        }
        int id = table[ordinal];
        if (id == UNRESOLVED) {
            id = resolve(material, true);
            if (id == UNRESOLVED) {
                return 0;
            }
            table[ordinal] = id;
        }
        return id;
    }

    private int blockId(Material material) {
        int ordinal = material.ordinal();
        int[] table = blockTypes;
        if (table == null || ordinal >= table.length) {
            table = grow(false, ordinal);
        }
        int id = table[ordinal];
        if (id == UNRESOLVED) {
            id = resolve(material, false);
            if (id == UNRESOLVED) {
                return 0;
            }
            table[ordinal] = id;
        }
        return id;
    }

    /**
     * Converts a Material to a ItemType.
     *
     * @param material The material
     * @return The itemtype
     */
    @Override
    public ItemType asItemType(Material material) {
        return ItemTypes.get(itemId(material));
    }

    @Override
    public BlockType asBlockType(Material material) {
        return BlockTypesCache.values[blockId(material)];
    }
""")

swap(CBA, """        try {
            checkNotNull(blockData);
            Material material = blockData.getMaterial();
            BlockType type = BlockTypes.getFromStateId(blockTypes[material.ordinal()]);
            List<? extends Property> propList = type.getProperties();
            if (propList.size() == 0) {
                return type.getDefaultState();
            }
            String properties = blockData.getAsString();
            return BlockState.get(type, properties, type.getDefaultState());
        } catch (NullPointerException e) {
            if (init()) {
                return adapt(blockData);
            }
            throw e;
        }
""", """        checkNotNull(blockData);
        Material material = blockData.getMaterial();
        BlockType type = BlockTypes.getFromStateId(blockId(material));
        List<? extends Property> propList = type.getProperties();
        if (propList.size() == 0) {
            return type.getDefaultState();
        }
        String properties = blockData.getAsString();
        return BlockState.get(type, properties, type.getDefaultState());
""")


def main():
    files = {}
    for path, old, new, count in PATCHES:
        full = os.path.join(ROOT, path)
        if path not in files:
            files[path] = open(full, encoding="utf-8").read()
        got = files[path].count(old)
        if got != count:
            raise SystemExit("в %s якорь встречается %d раз, ждали %d:\n%s"
                             % (path.split("/java/")[-1], got, count, old[:180]))
        files[path] = files[path].replace(old, new)
        print("   %-40s %5d -> %5d симв." % (path.split("/")[-1], len(old), len(new)))

    for path, text in files.items():
        open(os.path.join(ROOT, path), "w", encoding="utf-8").write(text)
        print("записано", path.split("/java/")[-1], len(text))


if __name__ == "__main__":
    main()
