#!/usr/bin/env python3
"""
启动18章测试任务并监控
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:9000"

def log(msg):
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

# 1. 设置测试模式为18章
log("设置测试模式为18章")
resp = requests.post(
    f"{BASE_URL}/api/run-mode",
    json={"mode": "test", "test_chapters": 18},
    timeout=10
)
log(f"设置响应: {resp.status_code} - {resp.json()}")

# 2. 创建任务
log("创建18章测试任务")
resp = requests.post(
    f"{BASE_URL}/api/tasks",
    json={"name": "18章最终测试-" + datetime.now().strftime("%m%d%H%M")},
    timeout=10
)
task_id = resp.json()["task_id"]
log(f"任务创建成功: {task_id}")

# 3. 启动任务
log("启动任务")
resp = requests.post(
    f"{BASE_URL}/api/tasks/{task_id}/start",
    timeout=10
)
log(f"启动响应: {resp.status_code}")

# 4. 开始监控
log("开始监控18章测试任务")
print("=" * 60)

start_time = time.time()
last_progress = {}

while True:
    try:
        # 获取任务状态
        resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=10)
        task = resp.json()
        status = task.get("status", "unknown")
        elapsed = int(time.time() - start_time)
        
        # 获取Agent状态
        agents_resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}/agents", timeout=5)
        agents = agents_resp.json() if agents_resp.status_code == 200 else {}
        
        # 显示状态
        time_str = datetime.now().strftime("%H:%M:%S")
        print(f"\n[{time_str}] 运行{elapsed}秒 | 状态: {status}")
        
        # 显示有进展的Agent
        for agent, data in agents.items():
            progress = data.get("progress_percent", 0)
            message = data.get("message", "")
            
            if agent not in last_progress or last_progress[agent] != progress or progress > 0:
                if progress > 0 or message:
                    print(f"  {agent}: {progress}% - {message}")
                    last_progress[agent] = progress
        
        # 检查是否完成
        if status in ["completed", "failed"]:
            print(f"\n任务{status}!")
            if status == "completed":
                print("🎉 18章测试成功完成！")
                print(f"任务ID: {task_id}")
                print(f"网页界面: http://127.0.0.1:9000")
                
                # 检查生成的文件
                try:
                    files_resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}/files", timeout=5)
                    if files_resp.status_code == 200:
                        files = files_resp.json()
                        print(f"生成文件数: {len(files)}")
                except:
                    pass
            else:
                print("任务失败")
                if "test_mode_reset_reason" in task:
                    print(f"失败原因: {task['test_mode_reset_reason']}")
            break
        
        # 每30秒检查一次
        time.sleep(30)
        
    except KeyboardInterrupt:
        print("\n监控被用户中断")
        break
    except Exception as e:
        print(f"监控错误: {e}")
        time.sleep(30)

print("\n" + "=" * 60)
print("监控结束")
print("=" * 60)