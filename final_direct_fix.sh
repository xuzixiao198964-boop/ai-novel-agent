#!/bin/bash
# 最终直接修复脚本

echo "最终直接修复"
echo "================================================================"

# 连接到服务器并执行修复
# 使用前先 export SSHPASS='你的root密码'（勿把密码写进仓库）
sshpass -e ssh -o StrictHostKeyChecking=no root@10.66.66.3 << 'EOF'

echo "1. 修复PlannerAgent"
cd /opt/ai-novel-agent

# 备份原文件
cp backend/app/agents/planner.py backend/app/agents/planner.py.backup.$(date +%s)

# 检查并修复__init__方法
if ! grep -q "def __init__" backend/app/agents/planner.py; then
    echo "  添加__init__方法到PlannerAgent"
    # 使用sed在class定义后添加__init__
    sed -i '/^class PlannerAgent(BaseAgent):/a\
    def __init__(self, task_id):\
        super().__init__(task_id)' backend/app/agents/planner.py
else
    echo "  PlannerAgent已有__init__方法"
fi

echo ""
echo "2. 修复其他Agent"
agents="trend style reviser scorer"

for agent in $agents; do
    file="backend/app/agents/${agent}.py"
    if [ -f "$file" ]; then
        if ! grep -q "def __init__" "$file"; then
            echo "  添加__init__方法到${agent}.py"
            # 获取正确的类名（首字母大写）
            class_name=$(echo "$agent" | sed 's/^./\u&/')Agent
            sed -i "/^class ${class_name}(BaseAgent):/a\
    def __init__(self, task_id):\\
        super().__init__(task_id)" "$file"
        else
            echo "  ${agent}.py已有__init__方法"
        fi
    else
        echo "  ${agent}.py不存在"
    fi
done

echo ""
echo "3. 验证修复"
echo "验证PlannerAgent:"
grep -n "__init__" backend/app/agents/planner.py
echo ""
echo "验证TrendAgent:"
grep -n "__init__" backend/app/agents/trend.py
echo ""
echo "验证StyleAgent:"
grep -n "__init__" backend/app/agents/style.py

echo ""
echo "4. 重启服务"
systemctl restart ai-novel-agent
sleep 3
echo "服务状态:"
systemctl status ai-novel-agent --no-pager | head -8

echo ""
echo "5. 测试修复"
cd /opt/ai-novel-agent
python3 << 'PYEOF'
import requests
import time

print("创建测试任务...")
resp = requests.post(
    'http://localhost:9000/api/tasks',
    json={'name': '最终修复测试', 'chapter_count': 1},
    timeout=10
)

if resp.status_code == 200:
    task_id = resp.json().get('task_id')
    print(f"任务ID: {task_id}")
    
    # 启动
    start_resp = requests.post(
        f'http://localhost:9000/api/tasks/{task_id}/start',
        timeout=10
    )
    print(f"启动: {start_resp.status_code}")
    
    # 监控
    print("\n监控执行...")
    for i in range(10):
        time.sleep(5)
        
        progress_resp = requests.get(
            f'http://localhost:9000/api/tasks/{task_id}/progress',
            timeout=10
        )
        
        if progress_resp.status_code == 200:
            progress = progress_resp.json()
            print(f"检查 {i+1}/10:")
            
            # 检查关键Agent
            for agent in ['TrendAgent', 'StyleAgent', 'PlannerAgent']:
                if agent in progress:
                    status = progress[agent].get('status', 'unknown')
                    if status == 'completed':
                        print(f"  ✓ {agent}: {status}")
                    elif status == 'running':
                        print(f"  → {agent}: {status}")
                    elif status == 'failed':
                        print(f"  ✗ {agent}: {status}")
                    else:
                        print(f"  · {agent}: {status}")
                else:
                    print(f"  · {agent}: 未开始")
            
            # 检查任务状态
            task_resp = requests.get(
                f'http://localhost:9000/api/tasks/{task_id}',
                timeout=10
            )
            
            if task_resp.status_code == 200:
                task_status = task_resp.json().get('status', 'unknown')
                if task_status == 'completed':
                    print(f"\n✅ 任务完成!")
                    break
                elif task_status == 'failed':
                    print(f"\n❌ 任务失败!")
                    break
        else:
            print(f"获取进度失败")
else:
    print(f"创建失败")

PYEOF

echo ""
echo "6. 检查错误日志"
journalctl -u ai-novel-agent --no-pager -n 10 | grep -i "error\|failed\|exception\|traceback\|TypeError" | grep -v "200 OK" | head -5

echo ""
echo "================================================================"
echo "修复完成!"

EOF

echo ""
echo "脚本执行完成"