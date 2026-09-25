package com.fastasyncworldedit.bukkit.adapter;

import com.fastasyncworldedit.core.nbt.FaweCompoundTag;
import com.sk89q.worldedit.world.registry.BlockMaterial;
import org.bukkit.Material;
import org.bukkit.block.data.BlockData;
import org.jetbrains.annotations.ApiStatus;

import javax.annotation.Nullable;

@ApiStatus.Internal
public abstract class BukkitBlockMaterial<B, BS> implements BlockMaterial {

    protected final B block;
    protected final BS blockState;
    private final BlockData blockData;
    private final Material craftMaterial;
    // 32-bit fork: раньше значение считалось в конструкторе. Конструктор
    // блок-сущности модового блока умеет полезть в конфиг своего мода, который
    // при сборке реестра ещё не загружен, и тогда наружу летело
    // IllegalStateException: Cannot get config value before config is loaded,
    // убивая весь блочный реестр. Теперь лениво и с повторами.
    private volatile FaweCompoundTag tile;
    private volatile boolean tileResolved;
    private int tileAttempts;
    private static int tileFailuresLogged;

    public BukkitBlockMaterial(B block, BS blockState, BlockData blockData) {
        this.block = block;
        this.blockState = blockState;
        this.blockData = blockData;
        this.craftMaterial = this.blockData.getMaterial();
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

    protected abstract FaweCompoundTag tileForBlock(B block);

    public B getBlock() {
        return this.block;
    }

    public BS getState() {
        return this.blockState;
    }

    public BlockData getBlockData() {
        return this.blockData;
    }

    @Override
    public boolean isBurnable() {
        return this.craftMaterial.isBurnable();
    }

    @Override
    public @Nullable FaweCompoundTag defaultTile() {
        return tile();
    }

    @Override
    public boolean hasContainer() {
        return tile() != null;
    }

    @Override
    public boolean isTile() {
        return tile() != null;
    }

    @Override
    public boolean isToolRequired() {
        // Removed in 1.16.1, this is not present in higher versions
        return false;
    }

}
