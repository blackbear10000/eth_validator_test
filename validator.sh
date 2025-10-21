#!/bin/bash
set -e

# ETH Validator Management Tool
# Unified command interface for Ethereum validator operations

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMMAND=$1
shift

# Ensure venv is activated
if [ -f "$SCRIPT_DIR/code/venv/bin/activate" ]; then
    source "$SCRIPT_DIR/code/venv/bin/activate"
fi

# Change to code directory for Python scripts
cd "$SCRIPT_DIR/code" 2>/dev/null || true

case "$COMMAND" in
    # Infrastructure
    start)
        echo "🚀 Starting infrastructure..."
        cd "$SCRIPT_DIR"
        ./start.sh quick-start
        ;;
    stop)
        echo "🛑 Stopping infrastructure..."
        cd "$SCRIPT_DIR"
        ./start.sh cleanup
        ;;
    status)
        echo "📊 Checking service status..."
        cd "$SCRIPT_DIR"
        ./start.sh status
        ;;
    
    # Key operations
    generate-keys)
        echo "🔑 Generating validator keys..."
        python3 core/validator_manager.py generate-keys "$@"
        ;;
    list-keys)
        echo "📋 Listing validator keys..."
        python3 core/validator_manager.py list-keys "$@"
        ;;
    backup)
        echo "💾 Creating backup..."
        python3 core/backup_system.py "$@"
        ;;
    
    # Deposit operations
    create-deposits)
        echo "💰 Creating deposit data..."
        python3 core/validator_manager.py create-deposits "$@"
        ;;
    submit-deposits)
        echo "📤 Submitting deposits..."
        python3 core/validator_manager.py submit-deposits "$@"
        ;;
    
    # Monitoring
    monitor)
        echo "📈 Monitoring validators..."
        python3 core/validator_manager.py monitor "$@"
        ;;
    
    # Quick deploy workflow
    deploy)
        echo "=== Quick Deploy Workflow ==="
        echo "🚀 Starting infrastructure..."
        cd "$SCRIPT_DIR"
        ./start.sh quick-start
        
        echo "🔑 Generating keys..."
        cd "$SCRIPT_DIR/code"
        python3 core/validator_manager.py generate-keys "$@"
        
        echo "💰 Creating deposits..."
        python3 core/validator_manager.py create-deposits "$@"
        
        echo ""
        echo "✅ Deployment ready!"
        echo "📁 Review deposit data: data/deposits/deposit_data-*.json"
        echo "📤 Submit deposits: ./validator.sh submit-deposits"
        echo "📈 Monitor: ./validator.sh monitor"
        ;;
    
    # Help
    help|--help|-h)
        show_help
        ;;
    
    *)
        if [ -n "$COMMAND" ]; then
            echo "❌ Unknown command: $COMMAND"
            echo ""
        fi
        show_help
        exit 1
        ;;
esac

function show_help() {
    echo "ETH Validator Management Tool"
    echo ""
    echo "Usage: ./validator.sh <command> [options]"
    echo ""
    echo "Infrastructure:"
    echo "  start              Start infrastructure (Vault, Web3Signer, Kurtosis)"
    echo "  stop               Stop all services"
    echo "  status             Check service status"
    echo ""
    echo "Key Management:"
    echo "  generate-keys      Generate validator keys"
    echo "  list-keys          List all keys"
    echo "  backup             Backup keys and mnemonic"
    echo ""
    echo "Deposit Operations:"
    echo "  create-deposits    Create deposit data"
    echo "  submit-deposits    Submit deposits to network"
    echo ""
    echo "Monitoring:"
    echo "  monitor            Monitor validator performance"
    echo ""
    echo "Quick Deploy:"
    echo "  deploy             Run full deployment workflow"
    echo ""
    echo "Examples:"
    echo "  ./validator.sh deploy --count 5"
    echo "  ./validator.sh generate-keys --count 10"
    echo "  ./validator.sh create-deposits"
    echo "  ./validator.sh monitor"
    echo ""
}
