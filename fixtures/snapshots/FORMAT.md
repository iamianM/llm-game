# Snapshot Fixture Format

Checked-in snapshots live here. Local saves live under `.game_saves/` and are gitignored.

A snapshot must include:

- `schema_version`
- canonical game state
- RNG state
- turn index
- day and phase
- state hash

During the POC, incompatible schema changes may regenerate checked-in snapshots instead of migrating them.
