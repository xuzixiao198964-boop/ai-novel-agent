#!/usr/bin/env python3
"""
在服务器上运行18章测试
"""

import paramiko
import time

hostname = "104.244.90.202"
port = 22
username = "root"
password = "v9wSxMxg92dp"
project_path = "/opt/ai-novel-agent"

def execute_command(ssh, command):
    """执行命令"""
    print(f"执行: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    return output, error

print("在服务器上运行18章DeepSeek API测试")
print("=" * 60)

try:
    # 连接服务器
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password, timeout=10)
    print("[OK] 连接成功")
    
    # 1. 上传测试脚本
    print("\n1. 上传测试脚本...")
    test_script = '''#!/usr/bin/env python3
import requests
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:9000"

print("DeepSeek API 18章测试 - 验证智能审核修复")
print("=" * 60)

# 设置测试模式
print("设置18章测试模式...")
resp = requests.post(f"{BASE_URL}/api/run-mode", json={"mode": "test", "test_chapters": 18}, timeout=10)
print(f"设置结果: {resp.status_code} - {resp.json()}")

# 创建任务
print("创建测试任务...")
task_name = f"修复验证-18章测试-{datetime.now().strftime('%m%d%H%M')}"
resp = requests.post(f"{BASE_URL}/api/tasks", json={"name": task_name}, timeout=10)
task_id = resp.json()["task_id"]
print(f"任务ID: {task_id}")

# 启动任务
print("启动任务...")
resp = requests.post(f"{BASE_URL}/api/tasks/{task_id}/start", timeout=10)
print(f"启动结果: {resp.status_code}")

print("\\n任务已启动，开始监控...")
print(f"网页界面: http://104.244.90.202:9000")
print(f"任务详情: {BASE_URL}/api/tasks/{task_id}")
print("=" * 60)

# 简单监控
start_time = time.time()
for i in range(30):  # 监控30分钟
    try:
        resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=5)
        task = resp.json()
        status = task.get("status", "unknown")
        elapsed = int(time.time() - start_time)
        
        print(f"第{elapsed}秒: 状态={status}")
        
        if status in ["completed", "failed"]:
            print(f"任务{status}!")
            if status == "completed":
                print("✅ 智能审核修复验证成功！")
            else:
                print("任务失败原因:", task.get("test_mode_reset_reason", "未知"))
            break
            
        time.sleep(30)
    except Exception as e:
        print(f"监控错误: {e}")
        time.sleep(30)

if time.time() - start_time >= 1800:
    print("监控超时（30分钟）")

print("测试完成")
'''
    
    # 写入测试脚本
    sftp = ssh.open_sftp()
    test_file = "/tmp/test_18ch.py"
    with sftp.file(test_file, "w") as f:
        f.write(test_script)
    sftp.close()
    print("[OK] 测试脚本已上传")
    
    # 2. 运行测试
    print("\n2. 运行18章测试...")
    cmd = f"cd {project_path}/backend && python {test_file}"
    execute_command(ssh, cmd)
    
    # 3. 实时监控
    print("\n3. 实时监控服务器日志...")
    print("（按Ctrl+C停止监控）")
    
    try:
        for i in range(10):  # 监控10次
            output, _ = execute_command(ssh, f"tail -n 5 {project_path}/backend/server.log")
            if output:
                print(f"日志更新: {output}")
            
            # 检查任务
            output, _ = execute_command(ssh, "curl -s http://localhost:9000/api/tasks | python3 -c \"import sys,json; data=json.load(sys.stdin); print('任务数:', len(data.get('tasks', []))); [print(f'{t[\"task_id\"]}: {t[\"status\"]} - {t.get(\"name\", \"\")[:20]}...') for t in data.get('tasks', [])[:3]]\" 2>/dev/null || echo '检查失败'")
            print(f"任务状态: {output}")
            
            time.sleep(30)
    except KeyboardInterrupt:
        print("\n监控停止")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("[OK] 测试已启动")
    print(f"请访问: http://104.244.90.202:9000")
    print("查看实时进度")
    print("=" * 60)
    
except Exception as e:
    print(f"[ERROR] 错误: {type(e).__name__}: {e}")

print("\n测试脚本执行完成")