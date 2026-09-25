package com.fastasyncworldedit.bukkit.adapter;

import com.sk89q.worldedit.registry.state.Property;
import com.sk89q.worldedit.world.block.BlockState;
import com.sk89q.worldedit.world.block.BlockType;
import com.sk89q.worldedit.world.block.BlockTypes;
import com.sk89q.worldedit.world.block.BlockTypesCache;
import com.sk89q.worldedit.world.item.ItemType;
import com.sk89q.worldedit.world.item.ItemTypes;
import org.bukkit.Material;
import org.bukkit.NamespacedKey;
import org.bukkit.block.data.BlockData;

import java.util.Arrays;
import java.util.List;

import static com.google.common.base.Preconditions.checkNotNull;

public abstract class CachedBukkitAdapter implements IBukkitAdapter {

    // 32-bit fork: раньше обе таблицы делались один раз по длине Material.values()
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

    /**
     * Create a WorldEdit BlockStateHolder from a Bukkit BlockData.
     *
     * @param blockData The Bukkit BlockData
     * @return The WorldEdit BlockState
     */
    @Override
    public BlockState adapt(BlockData blockData) {
        checkNotNull(blockData);
        Material material = blockData.getMaterial();
        BlockType type = BlockTypes.getFromStateId(blockId(material));
        List<? extends Property> propList = type.getProperties();
        if (propList.size() == 0) {
            return type.getDefaultState();
        }
        String properties = blockData.getAsString();
        return BlockState.get(type, properties, type.getDefaultState());
    }

    protected abstract int[] getIbdToOrdinal();

    protected abstract int[] getOrdinalToIbdID();

}
