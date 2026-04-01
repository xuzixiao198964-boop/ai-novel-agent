#!/bin/bash
# Simple live monitor

echo "Simple Live Monitor"
echo "=================="

# Connect and run monitor
# 使用前先 export SSHPASS='你的root密码'（勿把密码写进仓库）
sshpass -e ssh -o StrictHostKeyChecking=no root@10.66.66.3 << 'EOF'

cd /opt/ai-novel-agent

echo "1. Clean failed tasks..."
python3 -c "
import sqlite3
import os
import shutil

db = 'backend/data/novel_platform.db'
if os.path.exists(db):
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute('DELETE FROM tasks WHERE status = \"failed\"')
    conn.commit()
    conn.close()
    print('Database cleaned')
    
    tasks_dir = 'backend/data/tasks'
    if os.path.exists(tasks_dir):
        for item in os.listdir(tasks_dir):
            path = os.path.join(tasks_dir, item)
            if os.path.isdir(path):
                try:
                    shutil.rmtree(path)
                except:
                    pass
        print('Task dirs cleaned')
"

echo ""
echo "2. Create test task..."
cat > /tmp/create_test.py << 'CREATE_EOF'
import requests

print("Creating task...")
resp = requests.post(
    'http://localhost:9000/api/tasks',
    json={'name': 'Live Monitor Test', 'chapter_count': 1},
    timeout=10
)

if resp.status_code == 200:
    task_id = resp.json().get('task_id')
    print(f'Task ID: {task_id}')
    
    with open('/tmp/monitor_task.txt', 'w') as f:
        f.write(task_id)
    
    start_resp = requests.post(
        f'http://localhost:9000/api/tasks/{task_id}/start',
        timeout=10
    )
    print(f'Start: {start_resp.status_code}')
else:
    print(f'Create failed: {resp.status_code}, {resp.text}')
CREATE_EOF

python3 /tmp/create_test.py

echo ""
echo "3. Start live monitoring (20 minutes)..."
echo "========================================"

# Monitor for 20 minutes (120 checks * 10 seconds)
for i in {1..120}; do
    echo ""
    echo "Check $i/120"
    echo "-----------"
    
    # Get task ID
    task_id=$(cat /tmp/monitor_task.txt 2>/dev/null || echo "")
    
    if [ -z "$task_id" ]; then
        echo "No task ID"
        break
    fi
    
    # Check progress
    python3 -c "
import requests
import time

try:
    progress = requests.get(
        f'http://localhost:9000/api/tasks/{task_id}/progress',
        timeout=10
    ).json()
    
    print(f'Task status: {progress.get(\"task_status\", \"?\")}')
    
    # Check key agents
    agents = ['TrendAgent', 'StyleAgent', 'PlannerAgent']
    for agent in agents:
        if agent in progress:
            status = progress[agent].get('status', '?')
            print(f'  {agent}: {status}')
            
            if status == 'failed':
                print(f'    {agent} FAILED')
                # Check error
                import subprocess
                result = subprocess.run(
                    'journalctl -u ai-novel-agent --no-pager -n 3 | grep -i error',
                    shell=True, capture_output=True, text=True
                )
                if result.stdout:
                    print(f'    Error: {result.stdout[:100]}')
        else:
            print(f'  {agent}: not found')
    
    # Check DB
    try:
        task_info = requests.get(
            f'http://localhost:9000/api/tasks/{task_id}',
            timeout=10
        ).json()
        
        db_status = task_info.get('status', '?')
        print(f'  DB: {db_status}')
        
        if db_status == 'completed':
            print('\\nSUCCESS! Task completed')
            exit(0)
        elif db_status == 'failed':
            error = task_info.get('error', '?')
            print(f'\\nFAILED: {error[:50]}')
            exit(1)
    except:
        pass
        
except Exception as e:
    print(f'Check error: {e}')
"
    
    # Check exit code
    if [ $? -eq 0 ]; then
        echo ""
        echo "SUCCESS - Task completed!"
        break
    elif [ $? -eq 1 ]; then
        echo ""
        echo "FAILED - Task failed"
        break
    fi
    
    # Wait 10 seconds
    if [ $i -lt 120 ]; then
        sleep 10
    fi
done

echo ""
echo "Monitor completed"

EOF

echo ""
echo "Live monitor script completed"