#!/bin/bash

# Web3Signer Database Initialization Script using Official Migrations
# This script applies all PostgreSQL migration files in the correct order

echo "Initializing Web3Signer database with official migrations..."

# Apply migrations in order
psql -U postgres -d web3signer << 'EOF'
-- V00001__initial.sql
CREATE TABLE validators (
    id SERIAL PRIMARY KEY,
    public_key BYTEA NOT NULL,
    UNIQUE(public_key)
);
CREATE TABLE signed_blocks (
    validator_id INTEGER NOT NULL,
    slot NUMERIC(20) NOT NULL,
    signing_root BYTEA,
    FOREIGN KEY(validator_id) REFERENCES validators(id),
    UNIQUE (validator_id, slot)
);
CREATE TABLE signed_attestations (
    validator_id INTEGER,
    source_epoch NUMERIC(20) NOT NULL,
    target_epoch NUMERIC(20) NOT NULL,
    signing_root BYTEA,
    FOREIGN KEY(validator_id) REFERENCES validators(id),
    UNIQUE (validator_id, target_epoch)
);
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00002__removeUniqueConstraints.sql
ALTER TABLE signed_blocks DROP CONSTRAINT IF EXISTS signed_blocks_validator_id_slot_key;
ALTER TABLE signed_attestations DROP CONSTRAINT IF EXISTS signed_attestations_validator_id_target_epoch_key;
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00003__addLowWatermark.sql
CREATE TABLE low_watermarks (
    id SERIAL PRIMARY KEY,
    validator_id INTEGER NOT NULL,
    slot NUMERIC(20) NOT NULL,
    source_epoch NUMERIC(20) NOT NULL,
    target_epoch NUMERIC(20) NOT NULL,
    FOREIGN KEY(validator_id) REFERENCES validators(id),
    UNIQUE(validator_id)
);
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00004__addGenesisValidatorsRoot.sql
CREATE TABLE metadata (
    id INTEGER PRIMARY KEY,
    genesis_validators_root BYTEA NOT NULL
);
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00005__xnor_source_target_low_watermark.sql
CREATE OR REPLACE FUNCTION xnor_source_target_low_watermark() RETURNS TRIGGER AS $$
BEGIN
    IF (NEW.source_epoch = NEW.target_epoch) THEN
        RAISE EXCEPTION 'source_epoch and target_epoch must be different';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER xnor_source_target_low_watermark_trigger
    BEFORE INSERT OR UPDATE ON low_watermarks
    FOR EACH ROW EXECUTE PROCEDURE xnor_source_target_low_watermark();
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00006__signed_data_indexes.sql
CREATE INDEX signed_blocks_validator_id_slot_idx ON signed_blocks(validator_id, slot);
CREATE INDEX signed_attestations_validator_id_target_epoch_idx ON signed_attestations(validator_id, target_epoch);
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00007__add_db_version.sql
CREATE TABLE database_version (
    id INTEGER PRIMARY KEY,
    version INTEGER NOT NULL
);
-- Start at version 7, should have previously existed (but now represents migration index).
INSERT INTO database_version (id, version) VALUES (1, 7);
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00008__signed_data_unique_constraints.sql
ALTER TABLE signed_blocks ADD CONSTRAINT signed_blocks_validator_id_slot_unique UNIQUE (validator_id, slot);
ALTER TABLE signed_attestations ADD CONSTRAINT signed_attestations_validator_id_target_epoch_unique UNIQUE (validator_id, target_epoch);
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00009__upsert_validators.sql
CREATE OR REPLACE FUNCTION upsert_validator(validator_public_key BYTEA) RETURNS INTEGER AS $$
DECLARE
    validator_id INTEGER;
BEGIN
    -- Try to get the validator ID if it exists
    SELECT id INTO validator_id FROM validators WHERE public_key = validator_public_key;
    
    -- If validator doesn't exist, insert it
    IF validator_id IS NULL THEN
        INSERT INTO validators (public_key) VALUES (validator_public_key) RETURNING id INTO validator_id;
    END IF;
    
    RETURN validator_id;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION upsert_validators(validator_public_keys BYTEA[]) RETURNS INTEGER[] AS $$
DECLARE
    validator_ids INTEGER[];
    validator_id INTEGER;
    public_key BYTEA;
BEGIN
    validator_ids := ARRAY[]::INTEGER[];
    
    FOREACH public_key IN ARRAY validator_public_keys
    LOOP
        validator_id := upsert_validator(public_key);
        validator_ids := array_append(validator_ids, validator_id);
    END LOOP;
    
    RETURN validator_ids;
END;
$$ LANGUAGE plpgsql;
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00010__validator_enabled_status.sql
ALTER TABLE validators ADD COLUMN enabled BOOLEAN DEFAULT TRUE;
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00011__bigint_indexes.sql
CREATE INDEX signed_blocks_slot_idx ON signed_blocks(slot);
CREATE INDEX signed_attestations_source_epoch_idx ON signed_attestations(source_epoch);
CREATE INDEX signed_attestations_target_epoch_idx ON signed_attestations(target_epoch);
EOF

psql -U postgres -d web3signer << 'EOF'
-- V00012__add_highwatermark_metadata.sql
ALTER TABLE metadata
    ADD COLUMN high_watermark_epoch NUMERIC(20),
    ADD COLUMN high_watermark_slot NUMERIC(20);

-- inserted high watermark should be above low watermark

CREATE OR REPLACE FUNCTION check_high_watermarks() RETURNS TRIGGER AS $$
DECLARE
    max_slot NUMERIC(20);
    max_epoch NUMERIC(20);
BEGIN
SELECT MAX(slot) INTO max_slot FROM low_watermarks;
SELECT GREATEST(MAX(target_epoch), MAX(source_epoch)) INTO max_epoch FROM low_watermarks;

IF NEW.high_watermark_slot <= max_slot THEN
        RAISE EXCEPTION 'Insert/Update violates constraint: high_watermark_slot must be greater than max slot in low_watermarks table';
END IF;

IF NEW.high_watermark_epoch <= max_epoch THEN
        RAISE EXCEPTION 'Insert/Update violates constraint: high_watermark_epoch must be greater than max epoch in low_watermarks table';
END IF;

RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_before_insert_or_update_high_watermarks
    BEFORE INSERT OR UPDATE ON metadata
                         FOR EACH ROW EXECUTE PROCEDURE check_high_watermarks();


-- inserted low watermark should be below or the same as high watermark

CREATE OR REPLACE FUNCTION check_low_watermarks() RETURNS TRIGGER AS $$
DECLARE
    high_slot NUMERIC(20);
    high_epoch NUMERIC(20);
BEGIN
SELECT MIN(high_watermark_slot) INTO high_slot FROM metadata;
SELECT MIN(high_watermark_epoch) INTO high_epoch FROM metadata;

IF NEW.slot > high_slot THEN
        RAISE EXCEPTION 'Insert/Update violates constraint: low_watermark slot must be less than or equal to high_watermark_slot in the metadata table';
END IF;

IF NEW.source_epoch > high_epoch THEN
        RAISE EXCEPTION 'Insert/Update violates constraint: low_watermark source epoch must be less than or equal to high_watermark_epoch in the metadata table';
END IF;

IF NEW.target_epoch > high_epoch THEN
        RAISE EXCEPTION 'Insert/Update violates constraint: low_watermark target epoch must be less than or equal to high_watermark_epoch in the metadata table';
END IF;

RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER check_before_insert_or_update_low_watermarks
    BEFORE INSERT OR UPDATE ON low_watermarks
                         FOR EACH ROW EXECUTE PROCEDURE check_low_watermarks();


UPDATE database_version SET version = 12 WHERE id = 1;
EOF

echo "Database schema initialization with official migrations completed!"
