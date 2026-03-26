#!/bin/bash
# 部署修复到服务器 104.244.90.202

SERVER_IP="104.244.90.202"
SERVER_USER="root"  # 假设是root用户
PROJECT_PATH="/root/ai-novel-agent"  # 假设的项目路径

echo "部署智能审核修复到服务器 $SERVER_IP"
echo "=========================================="

# 1. 检查服务器连接
echo "1. 检查服务器连接..."
if ! ping -c 1 $SERVER_IP &> /dev/null; then
    echo "❌ 无法连接到服务器 $SERVER_IP"
    exit 1
fi
echo "✅ 服务器可连接"

# 2. 备份服务器上的文件
echo "2. 备份服务器文件..."
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_PATH/backend && cp app/agents/planner.py app/agents/planner.py.backup.$(date +%Y%m%d_%H%M%S)"

# 3. 上传修复文件
echo "3. 上传修复文件..."
scp app/agents/planner.py $SERVER_USER@$SERVER_IP:$PROJECT_PATH/backend/app/agents/planner.py

# 4. 上传测试脚本
echo "4. 上传测试脚本..."
scp test_deepseek_18ch.py $SERVER_USER@$SERVER_IP:$PROJECT_PATH/backend/

# 5. 重启服务器
echo "5. 重启服务器..."
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_PATH/backend && pkill -f uvicorn && sleep 2 && nohup uvicorn app.main:app --host 0.0.0.0 --port 9000 > server.log 2>&1 &"

# 6. 等待服务器启动
echo "6. 等待服务器启动..."
sleep 5

# 7. 检查服务器状态
echo "7. 检查服务器状态..."
if curl -s http://$SERVER_IP:9000/api/health | grep -q "ok"; then
    echo "✅ 服务器启动成功"
else
    echo "❌ 服务器启动失败"
    exit 1
fi

# 8. 运行测试
echo "8. 运行DeepSeek API测试..."
ssh $SERVER_USER@$SERVER_IP "cd $PROJECT_PATH/backend && python test_deepseek_18ch.py"

echo ""
echo "=========================================="
echo "部署完成！"
echo "服务器地址: http://$SERVER_IP:9000"
echo "查看日志: ssh $SERVER_USER@$SERVER_IP 'tail -f $PROJECT_PATH/backend/server.log'"
echo "=========================================="