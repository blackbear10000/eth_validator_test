#!/bin/bash
set -e

# Quick Deploy Helper Script
# One-command complete deployment for testing

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

COUNT=${1:-5}
NETWORK=${2:-mainnet}

echo "=== Quick Deploy: $COUNT validators on $NETWORK ==="
echo ""

# Start infrastructure
echo "🚀 Starting infrastructure..."
cd "$PROJECT_DIR"
./start.sh quick-start

# Wait for services to be ready
echo "⏳ Waiting for services to start..."
sleep 10

# Generate keys
echo "🔑 Generating $COUNT validator keys..."
cd "$PROJECT_DIR/code"
source venv/bin/activate 2>/dev/null || true
python3 core/validator_manager.py generate-keys --count $COUNT

# Backup mnemonic
echo "💾 Creating backup..."
python3 core/backup_system.py --type mnemonic

# Create deposits
echo "💰 Creating deposit data..."
python3 core/validator_manager.py create-deposits

echo ""
echo "✅ Ready to deploy!"
echo "📁 Review deposit data: data/deposits/deposit_data-*.json"
echo "📤 Submit deposits: ./validator.sh submit-deposits"
echo "📈 Monitor: ./validator.sh monitor"
echo ""
echo "🔐 IMPORTANT: Backup your mnemonic from data/keys/mnemonic.txt"
