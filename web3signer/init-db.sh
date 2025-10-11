#!/bin/bash

# Web3Signer Database Initialization Script
# Based on official documentation: https://docs.web3signer.consensys.io/how-to/configure-slashing-protection

echo "Initializing Web3Signer database schema..."

# Create the database schema tables
psql -U postgres -d web3signer << 'EOF'
-- Create database_version table
CREATE TABLE IF NOT EXISTS database_version (
    id INTEGER PRIMARY KEY,
    version INTEGER NOT NULL
);

-- Insert initial version
INSERT INTO database_version (id, version) VALUES (1, 12) ON CONFLICT (id) DO NOTHING;

-- Create slashing_protection table
CREATE TABLE IF NOT EXISTS slashing_protection (
    id SERIAL PRIMARY KEY,
    validator_id INTEGER NOT NULL,
    slot BIGINT NOT NULL,
    signing_root VARCHAR(66) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(validator_id, slot, signing_root)
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_slashing_protection_validator_id ON slashing_protection(validator_id);
CREATE INDEX IF NOT EXISTS idx_slashing_protection_slot ON slashing_protection(slot);

-- Create low_watermark table
CREATE TABLE IF NOT EXISTS low_watermark (
    id SERIAL PRIMARY KEY,
    validator_id INTEGER NOT NULL,
    slot BIGINT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(validator_id)
);

-- Create index for low_watermark
CREATE INDEX IF NOT EXISTS idx_low_watermark_validator_id ON low_watermark(validator_id);

EOF

echo "Database schema initialization completed!"
