package com.neom.oxagon.sap;

import java.time.Instant;
import java.util.Optional;

import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * Persists the SAP delta-sync high-watermark per entity, in the
 * `sap_sync_state` table.
 */
@Repository
public class SyncStateRepository {

    private final JdbcTemplate jdbc;

    public SyncStateRepository(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    public Optional<Instant> lastSyncedAt(String entity) {
        var rows = jdbc.queryForList(
            "SELECT last_synced_at FROM sap_sync_state WHERE entity = ?",
            Instant.class, entity);
        return rows.isEmpty() ? Optional.empty() : Optional.ofNullable(rows.get(0));
    }

    public void upsertLastSyncedAt(String entity, Instant at) {
        jdbc.update("""
            INSERT INTO sap_sync_state(entity, last_synced_at)
            VALUES (?, ?)
            ON CONFLICT (entity) DO UPDATE SET last_synced_at = EXCLUDED.last_synced_at
            """, entity, at);
    }
}
