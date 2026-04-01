#!/bin/bash
# AI小说生成Agent系统 - 部署启动脚本

set -e  # 遇到错误立即退出

echo "========================================"
echo "AI小说生成Agent系统部署启动"
echo "========================================"
echo "开始时间: $(date)"
echo ""

# 配置
SERVER_IP="104.244.90.202"
SERVER_USER="root"
DEPLOY_PACKAGE="deploy_package"
REMOTE_TEMP_DIR="/tmp/deploy_package"
PROJECT_PATH="/opt/ai-novel-agent"
BACKUP_DIR="/opt/ai-novel-agent-backups"
SERVICE_NAME="ai-novel-agent"

echo "目标服务器: ${SERVER_IP}"
echo "部署包: ${DEPLOY_PACKAGE}"
echo "项目路径: ${PROJECT_PATH}"
echo ""

# 检查部署包是否存在
if [ ! -d "${DEPLOY_PACKAGE}" ]; then
    echo "错误: 部署包 ${DEPLOY_PACKAGE} 不存在"
    echo "请先运行: python prepare_deployment_simple.py"
    exit 1
fi

echo "1. 检查服务器连接..."
if ! ssh ${SERVER_USER}@${SERVER_IP} "echo '连接成功'"; then
    echo "错误: 无法连接到服务器 ${SERVER_IP}"
    exit 1
fi
echo "   [OK] 服务器连接正常"
echo ""

echo "2. 上传部署包到服务器..."
scp -r ${DEPLOY_PACKAGE} ${SERVER_USER}@${SERVER_IP}:${REMOTE_TEMP_DIR}
echo "   [OK] 部署包上传完成"
echo ""

echo "3. 在服务器上执行部署..."
ssh ${SERVER_USER}@${SERVER_IP} << 'EOF'
set -e

echo "3.1 备份当前项目..."
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
mkdir -p /opt/ai-novel-agent-backups
if [ -d "/opt/ai-novel-agent" ]; then
    cd /opt/ai-novel-agent
    tar -czf /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz .
    echo "   [OK] 备份完成: /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz"
else
    echo "   [INFO] 项目目录不存在，跳过备份"
fi

echo ""
echo "3.2 停止服务..."
systemctl stop ai-novel-agent || true
echo "   [OK] 服务已停止"

echo ""
echo "3.3 更新代码..."
if [ -d "/opt/ai-novel-agent" ]; then
    # 备份现有配置
    if [ -f "/opt/ai-novel-agent/backend/.env" ]; then
        cp /opt/ai-novel-agent/backend/.env /tmp/.env.backup
    fi
    
    # 清空目录（保留venv）
    if [ -d "/opt/ai-novel-agent/backend/venv" ]; then
        mv /opt/ai-novel-agent/backend/venv /tmp/venv.backup
    fi
    
    rm -rf /opt/ai-novel-agent/*
else
    mkdir -p /opt/ai-novel-agent
fi

# 复制新代码
cp -r /tmp/deploy_package/* /opt/ai-novel-agent/

# 恢复venv
if [ -d "/tmp/venv.backup" ]; then
    rm -rf /opt/ai-novel-agent/backend/venv
    mv /tmp/venv.backup /opt/ai-novel-agent/backend/venv
fi

# 恢复配置
if [ -f "/tmp/.env.backup" ]; then
    cp /tmp/.env.backup /opt/ai-novel-agent/backend/.env
    rm /tmp/.env.backup
fi

echo "   [OK] 代码更新完成"

echo ""
echo "3.4 安装依赖..."
cd /opt/ai-novel-agent/backend
if [ -d "venv" ]; then
    source venv/bin/activate
    
    # 升级pip
    pip install --upgrade pip
    
    # 安装requirements.txt中的依赖
    if [ -f "requirements.txt" ]; then
        pip install -r requirements.txt
        echo "   [OK] 基础依赖安装完成"
    fi
    
    # 安装新模块的依赖
    pip install numpy scikit-learn || echo "   [WARNING] numpy/scikit-learn安装失败，可能需要手动安装"
else
    echo "   [WARNING] 虚拟环境不存在，跳过依赖安装"
fi

echo ""
echo "3.5 启动服务..."
systemctl start ai-novel-agent
sleep 5

if systemctl is-active --quiet ai-novel-agent; then
    echo "   [OK] 服务启动成功"
    
    # 显示服务状态
    echo ""
    echo "服务状态:"
    systemctl status ai-novel-agent --no-pager | head -20
else
    echo "   [FAIL] 服务启动失败"
    echo "查看日志: journalctl -u ai-novel-agent -n 50"
    exit 1
fi

echo ""
echo "3.6 等待服务完全启动..."
sleep 10

echo ""
echo "3.7 运行基础测试..."
cd /opt/ai-novel-agent
if [ -f "test_after_deployment.py" ]; then
    python test_after_deployment.py
    TEST_RESULT=$?
    if [ $TEST_RESULT -eq 0 ]; then
        echo "   [OK] 基础测试通过"
    else
        echo "   [WARNING] 基础测试失败，继续部署但需要检查"
    fi
else
    echo "   [INFO] 测试脚本不存在，跳过测试"
fi

echo ""
echo "========================================"
echo "部署完成!"
echo "========================================"
echo ""
echo "下一步操作:"
echo "1. 验证API: curl http://localhost:9000/api/health"
echo "2. 查看日志: journalctl -u ai-novel-agent -f"
echo "3. 创建测试任务验证完整功能"
echo "4. 监控性能指标"
echo ""
echo "如有问题可回滚到备份:"
echo "  tar -xzf /opt/ai-novel-agent-backups/backup_${TIMESTAMP}.tar.gz -C /opt/ai-novel-agent"
EOF

DEPLOY_RESULT=$?

echo ""
echo "========================================"
if [ $DEPLOY_RESULT -eq 0 ]; then
    echo "部署执行完成!"
    echo "请按照上述提示进行后续验证。"
else
    echo "部署执行失败!"
    echo "请检查错误信息并手动处理。"
fi
echo "========================================"
echo "结束时间: $(date)"

exit $DEPLOY_RESULT