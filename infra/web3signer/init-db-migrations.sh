#!/bin/bash

# Web3Signer Database Initialization Script using Official Migrations
# This script applies all PostgreSQL migration files in the correct order

echo "Initializing Web3Signer database with official migrations..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MIGRATIONS_DIR="$SCRIPT_DIR/migrations/postgresql"

# Check if migrations directory exists
if [ ! -d "$MIGRATIONS_DIR" ]; then
    echo "Error: Migrations directory not found at $MIGRATIONS_DIR"
    exit 1
fi

# Apply migrations in order
echo "Applying V00001__initial.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00001__initial.sql"

echo "Applying V00002__removeUniqueConstraints.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00002__removeUniqueConstraints.sql"

echo "Applying V00003__addLowWatermark.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00003__addLowWatermark.sql"

echo "Applying V00004__addGenesisValidatorsRoot.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00004__addGenesisValidatorsRoot.sql"

echo "Applying V00005__xnor_source_target_low_watermark.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00005__xnor_source_target_low_watermark.sql"

echo "Applying V00006__signed_data_indexes.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00006__signed_data_indexes.sql"

echo "Applying V00007__add_db_version.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00007__add_db_version.sql"

echo "Applying V00008__signed_data_unique_constraints.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00008__signed_data_unique_constraints.sql"

echo "Applying V00009__upsert_validators.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00009__upsert_validators.sql"

echo "Applying V00010__validator_enabled_status.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00010__validator_enabled_status.sql"

echo "Applying V00011__bigint_indexes.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00011__bigint_indexes.sql"

echo "Applying V00012__add_highwatermark_metadata.sql..."
psql -U postgres -d web3signer -f "$MIGRATIONS_DIR/V00012__add_highwatermark_metadata.sql"

echo "Database schema initialization with official migrations completed!"

# Verify the final database version
echo "Verifying database version..."
psql -U postgres -d web3signer -c "SELECT * FROM database_version;"

echo "Database initialization completed successfully!"