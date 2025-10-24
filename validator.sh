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
    
    # Pool management commands
    init-pool)
        echo "🏗️  Initializing key pool..."
        python3 core/validator_manager.py init-pool "$@"
        ;;
    activate-keys)
        echo "🔧 Activating keys from pool..."
        python3 core/validator_manager.py activate-keys "$@"
        ;;
    pool-status)
        echo "📊 Checking key pool status..."
        python3 core/validator_manager.py pool-status "$@"
        ;;
    
    # Deposit operations
    create-deposits)
        echo "💰 Creating deposit data..."
        python3 core/validator_manager.py create-deposits "$@"
        ;;
    create-deposits-with-fork-version)
        echo "💰 Creating deposit data with custom fork version..."
        python3 "$SCRIPT_DIR/scripts/create_deposits_with_fork_version.py" "$@"
        ;;
    create-deposits-with-address)
        echo "💰 Creating deposit data with custom withdrawal address..."
        python3 core/validator_manager.py create-deposits-with-address "$@"
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
    
    # Testing
    test-import)
        echo "🧪 Testing Vault import..."
        python3 core/validator_manager.py test-import "$@"
        ;;
    clean)
        echo "🧹 Cleaning all keys (local files and Vault)..."
        python3 core/validator_manager.py clean "$@"
        ;;
    check-status)
        echo "🔍 Checking validator activation status..."
        python3 core/validator_manager.py check-status "$@"
        ;;
    validate-deposits)
        echo "🔍 Validating deposit data..."
        python3 core/validator_manager.py validate-deposits "$@"
        ;;
    
    load-keys)
        echo "🔧 Loading keys to Web3Signer..."
        python3 core/web3signer_manager.py load
        ;;
    
    web3signer-status)
        echo "📊 Checking Web3Signer status..."
        python3 core/web3signer_manager.py status
        ;;
    
    verify-keys)
        echo "🔍 Verifying keys in Web3Signer..."
        python3 core/web3signer_manager.py verify
        ;;
    
    web3signer-deploy)
        echo "🚀 Web3Signer 完整部署工作流..."
        python3 utils/web3signer_workflow.py deploy --count ${2:-5} --client ${3:-prysm}
        ;;
    
    web3signer-workflow-status)
        echo "📊 Web3Signer 系统状态..."
        python3 utils/web3signer_workflow.py status
        ;;
    
    web3signer-troubleshoot)
        echo "🔧 Web3Signer 故障排除..."
        python3 utils/web3signer_workflow.py troubleshoot
        ;;
    
    start-validator)
        echo "🚀 启动 Validator Client..."
        python3 "$SCRIPT_DIR/scripts/start_validator_client.py" "$@"
        ;;
    
    check-services)
        echo "🔍 检查服务状态..."
        python3 "$SCRIPT_DIR/scripts/start_validator_client.py" --check-services
        ;;
    
    detect-kurtosis-ports)
        echo "🔍 检测 Kurtosis 网络端口..."
        python3 "$SCRIPT_DIR/scripts/detect_kurtosis_ports.py" --save
        ;;
    
    setup-kurtosis-alternative)
        echo "🔧 设置 Kurtosis 替代方案..."
        python3 "$SCRIPT_DIR/scripts/setup_kurtosis_alternative.py"
        ;;
    
    debug-kurtosis)
        echo "🔍 调试 Kurtosis 输出格式..."
        python3 "$SCRIPT_DIR/scripts/debug_kurtosis_output.py"
        ;;
    
    test-kurtosis)
        echo "🧪 测试 Kurtosis 命令..."
        python3 "$SCRIPT_DIR/scripts/test_kurtosis_command.py"
        ;;
    
    check-clients)
        echo "🔍 检查 Validator Client 安装状态..."
        python3 "$SCRIPT_DIR/scripts/check_validator_clients.py"
        ;;
    
    install-commands)
        echo "📋 显示 Validator Client 安装命令..."
        python3 "$SCRIPT_DIR/scripts/check_validator_clients.py" --install-commands
        ;;
    
    debug-prysm)
        echo "🔍 调试 Prysm 安装问题..."
        python3 "$SCRIPT_DIR/scripts/debug_prysm_installation.py"
        ;;
    
    test-prysm-config)
        echo "🧪 测试 Prysm 配置生成..."
        python3 "$SCRIPT_DIR/scripts/test_prysm_config.py"
        ;;
    
    detect-prysm-grpc)
        echo "🔍 检测 Prysm gRPC 端口..."
        python3 "$SCRIPT_DIR/scripts/detect_prysm_grpc_port.py"
        ;;
    
    clear-port-cache)
        echo "🧹 清除端口缓存..."
        python3 "$SCRIPT_DIR/scripts/clear_port_cache.py"
        ;;

    select-beacon-api)
        echo "🔍 智能选择 Beacon API..."
        python3 "$SCRIPT_DIR/scripts/select_beacon_api.py"
        ;;

    test-grpc-conversion)
        echo "🧪 测试 gRPC 转换逻辑..."
        python3 "$SCRIPT_DIR/scripts/test_grpc_conversion.py"
        ;;

    test-prysm-ports)
        echo "🧪 测试 Prysm 端口检测..."
        python3 "$SCRIPT_DIR/scripts/test_prysm_ports.py"
        ;;

    debug-port-parsing)
        echo "🔍 调试端口解析..."
        python3 "$SCRIPT_DIR/scripts/debug_port_parsing.py"
        ;;

    debug-service-matching)
        echo "🔍 调试服务名称匹配..."
        python3 "$SCRIPT_DIR/scripts/debug_service_matching.py"
        ;;

    debug-prysm-parsing)
        echo "🔍 调试 Prysm 端口解析..."
        python3 "$SCRIPT_DIR/scripts/debug_prysm_parsing.py"
        ;;

    test-port-detection)
        echo "🧪 测试端口检测结果..."
        python3 "$SCRIPT_DIR/scripts/test_port_detection_result.py"
        ;;

    debug-multiline-parsing)
        echo "🔍 调试多行端口解析..."
        python3 "$SCRIPT_DIR/scripts/debug_multiline_parsing.py"
        ;;

    manage-keys)
        echo "🔑 管理验证者密钥..."
        python3 "$SCRIPT_DIR/scripts/manage_validator_keys.py" "$@"
        ;;

    check-beacon-sync)
        echo "🔍 检查 Beacon 链同步状态..."
        python3 "$SCRIPT_DIR/scripts/check_beacon_sync.py"
        ;;

    check-validator-status)
        echo "🔍 检查验证者状态..."
        python3 "$SCRIPT_DIR/scripts/check_validator_status.py"
        ;;
    
    test-vault-paths)
        echo "🔍 测试 Vault 路径和密钥访问..."
        python3 "$SCRIPT_DIR/scripts/test_vault_paths.py"
        ;;
    
    test-key-format)
        echo "🔍 测试密钥格式和存储流程..."
        python3 "$SCRIPT_DIR/scripts/test_key_format.py"
        ;;
    
    test-web3signer-config)
        echo "🔍 测试 Web3Signer 配置和 Vault 连接..."
        python3 "$SCRIPT_DIR/scripts/test_web3signer_config.py"
        ;;
    
    test-web3signer-connection)
        echo "🔍 测试 Web3Signer 连接和 HA 设置..."
        python3 "$SCRIPT_DIR/scripts/test_web3signer_connection.py"
        ;;
    
    test-deposit-network)
        echo "🔍 测试存款网络配置..."
        python3 "$SCRIPT_DIR/scripts/test_deposit_network.py"
        ;;
    
    diagnose-web3signer)
        echo "🔍 诊断 Web3Signer 连接问题..."
        python3 "$SCRIPT_DIR/scripts/diagnose_web3signer.py"
        ;;
    
    debug-web3signer-connection)
        echo "🔍 诊断 Web3Signer 连接问题..."
        python3 "$SCRIPT_DIR/scripts/debug_web3signer_connection.py"
        ;;
    
    fix-web3signer-connection)
        echo "🔧 修复 Web3Signer 连接问题..."
        python3 "$SCRIPT_DIR/scripts/fix_web3signer_connection.py"
        ;;
    
    restart-web3signer)
        echo "🔄 重启 Web3Signer 服务..."
        python3 "$SCRIPT_DIR/scripts/fix_web3signer_connection.py" --restart
        ;;
    
    analyze-prysm-web3signer)
        echo "🔍 分析 Prysm-Web3Signer 连接问题..."
        python3 "$SCRIPT_DIR/scripts/analyze_prysm_web3signer_issue.py"
        ;;
    
    test-haproxy)
        echo "🔍 测试 HAProxy 配置..."
        python3 "$SCRIPT_DIR/scripts/test_haproxy_config.py"
        ;;
    
    test-web3signer-startup)
        echo "🔍 测试 Web3Signer 启动状态..."
        python3 "$SCRIPT_DIR/scripts/test_web3signer_startup.py"
        ;;
    
    setup-web3signer-vault)
        echo "🔧 为 Web3Signer 设置 Vault 密钥存储..."
        python3 "$SCRIPT_DIR/scripts/setup_web3signer_vault.py"
        ;;
    
    clean-keys)
        echo "🧹 清理 Web3Signer keys 目录..."
        python3 "$SCRIPT_DIR/scripts/clean_web3signer_keys.py"
        ;;
    
    reset-web3signer)
        echo "🔄 重置 Web3Signer 并重新加载密钥..."
        python3 "$SCRIPT_DIR/scripts/reset_web3signer.py"
        ;;
    
    fix-database)
        echo "🔧 修复数据库问题..."
        python3 "$SCRIPT_DIR/scripts/fix_database.py"
        ;;
    
    reset-database)
        echo "🔄 完全重置数据库..."
        python3 "$SCRIPT_DIR/scripts/reset_database.py"
        ;;
    
    manual-fix-database)
        echo "🔧 手动修复数据库..."
        python3 "$SCRIPT_DIR/scripts/manual_fix_database.py"
        ;;
    
    fix-database-version)
        echo "🔧 修复数据库版本..."
        python3 "$SCRIPT_DIR/scripts/fix_database_version.py"
        ;;
    
    create-database-tables)
        echo "📋 创建数据库表..."
        python3 "$SCRIPT_DIR/scripts/create_database_tables.py"
        ;;
    
    simple-reset)
        echo "🔄 简单重置数据库..."
        python3 "$SCRIPT_DIR/scripts/simple_reset.py"
        ;;
    
    direct-reset)
        echo "🔄 直接重置数据库..."
        python3 "$SCRIPT_DIR/scripts/direct_reset.py"
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
        echo "ETH Validator Management Tool"
        echo ""
        echo "Usage: ./validator.sh <command> [options]"
        echo ""
        echo "Infrastructure:"
        echo "  start               Start all services"
        echo "  stop                Stop all services"
        echo "  status              Check service status"
        echo ""
        echo "Key Management:"
        echo "  generate-keys       Generate validator keys"
        echo "  list-keys           List all keys"
        echo "  backup              Backup keys"
        echo "  clean               Clean all keys (local files and Vault)"
        echo ""
        echo "Deposit Operations:"
        echo "  create-deposits    Create deposit data"
        echo "  submit-deposits    Submit deposits to network"
        echo "  validate-deposits  Validate deposit data using ethstaker-deposit-cli"
        echo ""
        echo "Web3Signer Integration:"
        echo "  load-keys              Load validator keys to Web3Signer"
        echo "  web3signer-status      Check Web3Signer status and loaded keys"
    echo "  web3signer-workflow-status Check Web3Signer workflow status"
        echo "  web3signer-workflow-status Check Web3Signer workflow status"
        echo "  verify-keys            Verify keys are loaded in Web3Signer"
        echo "  web3signer-deploy      Complete Web3Signer deployment workflow"
        echo "  web3signer-troubleshoot Web3Signer troubleshooting guide"
        echo "  fix-database           Fix PostgreSQL database issues"
        echo "  reset-database         Complete database reset (destructive)"
        echo "  manual-fix-database    Manual database table recreation"
        echo "  fix-database-version   Fix database version mismatch"
        echo ""
        echo "Monitoring:"
        echo "  monitor            Monitor validator performance"
        echo ""
        echo "Quick Deploy:"
        echo "  deploy             Run full deployment workflow"
        echo ""
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
    echo "  clean              Clean all keys and data"
    echo "  check-status       Check validator activation status"
    echo ""
    echo "Deposit Operations:"
    echo "  create-deposits    Create deposit data"
    echo "  submit-deposits    Submit deposits to network"
    echo "  validate-deposits  Validate deposit data using ethstaker-deposit-cli"
    echo ""
    echo "Web3Signer Integration:"
    echo "  load-keys              Load validator keys to Web3Signer"
    echo "  web3signer-status      Check Web3Signer status and loaded keys"
    echo "  web3signer-workflow-status Check Web3Signer workflow status"
    echo "  verify-keys            Verify keys are loaded in Web3Signer"
    echo "  web3signer-deploy      Complete Web3Signer deployment workflow"
    echo "  web3signer-troubleshoot Web3Signer troubleshooting guide"
    echo "  fix-database           Fix PostgreSQL database issues"
    echo "  reset-database         Complete database reset (destructive)"
    echo "  manual-fix-database    Manual database table recreation"
    echo "  fix-database-version   Fix database version mismatch"
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
