package com.fastasyncworldedit.core.internal.simd;

import com.fastasyncworldedit.core.queue.IBlocks;
import com.sk89q.worldedit.world.block.BlockTypesCache;
import jdk.incubator.vector.IntVector;
import jdk.incubator.vector.VectorSpecies;
import org.jetbrains.annotations.ApiStatus;

@ApiStatus.Internal
public class VectorFacade {
    private final IBlocks blocks;
    private int layer;
    private int index;
    private int[] data;

    VectorFacade(final IBlocks blocks) {
        this.blocks = blocks;
    }

    public IntVector get(VectorSpecies<Integer> species) {
        if (this.data == null) {
            load();
        }
        return IntVector.fromArray(species, this.data, this.index);
    }

    public IntVector getOrZero(VectorSpecies<Integer> species) {
        if (this.data == null) {
            return IntVector.zero(species);
        }
        return IntVector.fromArray(species, this.data, this.index);
    }

    public void setOrIgnore(IntVector vector) {
        if (this.data == null) {
            if (vector.eq(BlockTypesCache.ReservedIDs.__RESERVED__).allTrue()) {
                return;
            }
            load();
        }
        vector.intoArray(this.data, this.index);
    }

    private void load() {
        this.data = this.blocks.load(this.layer);
    }

    public void setLayer(int layer) {
        this.layer = layer;
        this.data = null;
    }

    public void setIndex(int index) {
        this.index = index;
    }

    public void setData(int[] data) {
        this.data = data;
    }

}
