#!/bin/bash
# 部署修复到服务器

SERVER="10.66.66.3"
USER="root"
PASSWORD="${DEPLOY_SSH_PASSWORD:?请先 export DEPLOY_SSH_PASSWORD=你的root密码}"
REMOTE_DIR="/opt/ai-novel-agent"

echo "部署修复到服务器 $SERVER..."
echo "================================================================"

# 1. 备份服务器文件
echo "1. 备份服务器文件..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $USER@$SERVER "
cd $REMOTE_DIR
BACKUP_DIR=\"backup-\$(date +%Y%m%d_%H%M%S)\"
mkdir -p \$BACKUP_DIR
cp -r backend/app/agents \$BACKUP_DIR/
cp backend/app/core/pipeline.py \$BACKUP_DIR/
cp backend/app/core/pipeline_fixed.py \$BACKUP_DIR/
echo \"备份完成到: \$BACKUP_DIR\"
"

# 2. 部署修复后的Agent文件
echo "2. 部署修复后的Agent文件..."

# TrendAgent
echo "部署 TrendAgent..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no backend/app/agents/trend.py $USER@$SERVER:$REMOTE_DIR/backend/app/agents/

# StyleAgent
echo "部署 StyleAgent..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no backend/app/agents/style.py $USER@$SERVER:$REMOTE_DIR/backend/app/agents/

# PlannerAgent
echo "部署 PlannerAgent..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no backend/app/agents/planner.py $USER@$SERVER:$REMOTE_DIR/backend/app/agents/

# ReviserAgent
echo "部署 ReviserAgent..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no backend/app/agents/reviser.py $USER@$SERVER:$REMOTE_DIR/backend/app/agents/

# ScorerAgent
echo "部署 ScorerAgent..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no backend/app/agents/scorer.py $USER@$SERVER:$REMOTE_DIR/backend/app/agents/

# agents/__init__.py
echo "部署 agents/__init__.py..."
sshpass -p "$PASSWORD" scp -o StrictHostKeyChecking=no backend/app/agents/__init__.py $USER@$SERVER:$REMOTE_DIR/backend/app/agents/

# 3. 测试修复
echo "3. 测试修复..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $USER@$SERVER "
cd $REMOTE_DIR
cat > test_agents.py << 'EOF'
import sys
sys.path.insert(0, 'backend/app')

try:
    from agents.trend import TrendAgent
    from agents.style import StyleAgent
    from agents.planner import PlannerAgent
    from agents.reviser import ReviserAgent
    from agents.scorer import ScorerAgent
    
    print(\"测试Agent初始化...\")
    
    test_task_id = \"test_task_123\"
    
    agents = [
        (\"TrendAgent\", TrendAgent(test_task_id)),
        (\"StyleAgent\", StyleAgent(test_task_id)),
        (\"PlannerAgent\", PlannerAgent(test_task_id)),
        (\"ReviserAgent\", ReviserAgent(test_task_id)),
        (\"ScorerAgent\", ScorerAgent(test_task_id)),
    ]
    
    for name, agent in agents:
        print(f\"{name}: 初始化成功, task_id={agent.task_id}, name={agent.name}\")
    
    print(\"所有Agent初始化测试通过!\")
    
except Exception as e:
    print(f\"测试失败: {e}\")
    import traceback
    traceback.print_exc()
EOF

python3 test_agents.py
"

# 4. 重启服务
echo "4. 重启服务..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $USER@$SERVER "
systemctl restart ai-novel-agent
sleep 3
systemctl status ai-novel-agent --no-pager | head -20
"

# 5. 测试API
echo "5. 测试API..."
sshpass -p "$PASSWORD" ssh -o StrictHostKeyChecking=no $USER@$SERVER "
cd $REMOTE_DIR
cat > test_api.py << 'EOF'
import requests
import json
import time

server = \"http://localhost:9000\"

print(\"测试API...\")

# 测试健康检查
try:
    resp = requests.get(f\"{server}/api/health\", timeout=5)
    print(f\"健康检查: {resp.status_code}, {resp.json()}\")
except Exception as e:
    print(f\"健康检查失败: {e}\")

# 测试创建任务
try:
    resp = requests.post(
        f\"{server}/api/tasks\",
        json={\"name\": \"API测试任务\"},
        timeout=10
    )
    if resp.status_code == 200:
        task_data = resp.json()
        task_id = task_data.get(\"task_id\")
        print(f\"创建任务成功: {task_id}\")
        
        # 测试启动任务
        time.sleep(1)
        start_resp = requests.post(
            f\"{server}/api/tasks/{task_id}/start\",
            timeout=10
        )
        print(f\"启动任务: {start_resp.status_code}, {start_resp.text}\")
        
        # 检查任务状态
        time.sleep(2)
        progress_resp = requests.get(
            f\"{server}/api/tasks/{task_id}/progress\",
            timeout=10
        )
        if progress_resp.status_code == 200:
            progress = progress_resp.json()
            print(f\"任务进度: {json.dumps(progress, indent=2, ensure_ascii=False)}\")
        else:
            print(f\"获取进度失败: {progress_resp.status_code}\")
            
    else:
        print(f\"创建任务失败: {resp.status_code}, {resp.text}\")
        
except Exception as e:
    print(f\"API测试失败: {e}\")
    import traceback
    traceback.print_exc()
EOF

python3 test_api.py
"

echo "================================================================"
echo "部署完成!"
echo ""
echo "请在前端测试'创建并启动'按钮，检查任务是否正常创建和运行。"