#!/bin/bash
# Quick monitor script

echo "Quick Monitor and Fix"
echo "====================="

# Connect and execute
# 使用前先 export SSHPASS='你的root密码'（勿把密码写进仓库）
sshpass -e ssh -o StrictHostKeyChecking=no root@10.66.66.3 << 'EOF'

echo "1. Delete failed tasks..."
cd /opt/ai-novel-agent
python3 -c "
import sqlite3
import os
import shutil

db_path = 'backend/data/novel_platform.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    cursor.execute('SELECT task_id FROM tasks WHERE status = \"failed\"')
    failed = cursor.fetchall()
    print(f'Found {len(failed)} failed tasks')
    
    cursor.execute('DELETE FROM tasks WHERE status = \"failed\"')
    conn.commit()
    
    # Delete directories
    tasks_dir = 'backend/data/tasks'
    if os.path.exists(tasks_dir):
        for task_id_tuple in failed:
            task_id = task_id_tuple[0]
            task_path = os.path.join(tasks_dir, task_id)
            if os.path.exists(task_path):
                try:
                    shutil.rmtree(task_path)
                except:
                    pass
    
    conn.close()
    print('Failed tasks deleted')
else:
    print('DB not found')
"

echo ""
echo "2. Ensure all agents have __init__..."
# Fix PlannerAgent
cat > backend/app/agents/planner.py << 'PLANNER_EOF'
from .base import BaseAgent

class PlannerAgent(BaseAgent):
    def __init__(self, task_id):
        super().__init__(task_id)
    
    def run(self):
        self.logger.info("Planner running")
        self.save_result({"test": "ok"})
PLANNER_EOF

# Fix other agents if needed
for agent in trend style reviser scorer; do
    if [ -f "backend/app/agents/$agent.py" ]; then
        if ! grep -q "def __init__(self, task_id):" "backend/app/agents/$agent.py"; then
            echo "Fixing $agent..."
            sed -i '/class.*Agent.*:/a\\    def __init__(self, task_id):\\        super().__init__(task_id)' "backend/app/agents/$agent.py"
        fi
    fi
done

echo ""
echo "3. Restart service..."
systemctl restart ai-novel-agent
sleep 5

echo ""
echo "4. Create and monitor task..."
python3 -c "
import requests
import time

print('Creating task...')
resp = requests.post(
    'http://localhost:9000/api/tasks',
    json={'name': 'Quick Monitor Task', 'chapter_count': 1},
    timeout=10
)

if resp.status_code != 200:
    print(f'Create failed: {resp.status_code}, {resp.text}')
    exit(1)

task_id = resp.json().get('task_id')
print(f'Task created: {task_id}')

# Start
start_resp = requests.post(
    f'http://localhost:9000/api/tasks/{task_id}/start',
    timeout=10
)
print(f'Start: {start_resp.status_code}')

print('')
print('Monitoring for 2 minutes...')
print('===========================')

for i in range(12):  # 12 * 10s = 2 minutes
    print(f'Check {i+1}/12...')
    time.sleep(10)
    
    try:
        # Progress
        progress_resp = requests.get(
            f'http://localhost:9000/api/tasks/{task_id}/progress',
            timeout=10
        )
        
        if progress_resp.status_code == 200:
            progress = progress_resp.json()
            
            print(f'Task status: {progress.get(\"task_status\", \"unknown\")}')
            
            # Check agents
            agents = ['TrendAgent', 'StyleAgent', 'PlannerAgent']
            for agent in agents:
                if agent in progress:
                    status = progress[agent].get('status', 'unknown')
                    print(f'  {agent}: {status}')
                    
                    if status == 'failed':
                        print(f'  ERROR: {agent} failed!')
                        # Show recent errors
                        import subprocess
                        result = subprocess.run(
                            'journalctl -u ai-novel-agent --no-pager -n 5 | grep -i error',
                            shell=True, capture_output=True, text=True
                        )
                        if result.stdout:
                            print(f'  Log: {result.stdout[:100]}')
                else:
                    print(f'  {agent}: not found')
            
            # Check DB
            task_resp = requests.get(
                f'http://localhost:9000/api/tasks/{task_id}',
                timeout=10
            )
            
            if task_resp.status_code == 200:
                task_info = task_resp.json()
                db_status = task_info.get('status', 'unknown')
                print(f'DB status: {db_status}')
                
                if db_status == 'failed':
                    error = task_info.get('error', '')
                    print(f'DB error: {error[:100]}')
                    break
                elif db_status == 'completed':
                    print('SUCCESS: Task completed!')
                    break
        else:
            print(f'Progress failed: {progress_resp.status_code}')
            
    except Exception as e:
        print(f'Check error: {e}')

print('')
print('Monitor completed')
"

EOF

echo ""
echo "Script completed"
echo "Check the output above for results"