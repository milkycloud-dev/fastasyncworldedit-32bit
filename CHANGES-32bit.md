# Changes of the 32-bit fork

## 2.15.4-32bit.1 (2026-09-25)

Based on FastAsyncWorldEdit 2.15.4.

- Block state ordinals widened from 16 bit (`char`) to 32 bit (`int`) in 46 files, which lifts the ceiling of 65 536 block states.
- The schematic palette no longer uses `Character.MAX_VALUE` as the empty slot marker.
- `DiskOptimizedClipboard` stores 4 bytes per block; its format version is 3, so older buffers are not misread.
- `BlockTypesCache.generateStateOrdinals` no longer advances past states that were never added.
- A modded block that fails during registration is skipped by name instead of breaking the whole block registry.
- `BukkitBlockMaterial` creates block entities lazily instead of during registry construction.
- `CachedBukkitAdapter` grows its `Material` tables to the ordinals it actually sees.
- Only the 1.21 adapter is built.
