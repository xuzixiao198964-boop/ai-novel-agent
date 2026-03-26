#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
最终测试：验证修复是否有效
"""

import requests
import time
import json

BASE_URL = "http://127.0.0.1:9000"

print("=" * 60)
print("最终测试：验证审核机制修复")
print("=" * 60)

# 1. 设置测试模式为3章
print("1. 设置测试模式为3章")
resp = requests.post(
    f"{BASE_URL}/api/run-mode",
    json={"mode": "test", "test_chapters": 3},
    timeout=10
)
print(f"响应: {resp.status_code}")
if resp.status_code == 200:
    print(f"设置成功: {resp.json()}")
else:
    print(f"设置失败: {resp.text}")
    exit(1)

# 2. 创建任务
print("\n2. 创建测试任务")
resp = requests.post(
    f"{BASE_URL}/api/tasks",
    json={"name": "最终修复测试-3章"},
    timeout=10
)
if resp.status_code != 200:
    print(f"创建任务失败: {resp.text}")
    exit(1)

task_id = resp.json()["task_id"]
print(f"任务创建成功: {task_id}")

# 3. 启动任务
print("\n3. 启动任务")
resp = requests.post(
    f"{BASE_URL}/api/tasks/{task_id}/start",
    timeout=10
)
if resp.status_code != 200:
    print(f"启动失败: {resp.text}")
    exit(1)
print("任务启动成功")

# 4. 监控进度
print("\n4. 监控进度（最多5分钟）")
print("-" * 40)

start_time = time.time()
timeout = 300  # 5分钟

while time.time() - start_time < timeout:
    try:
        # 获取任务状态
        resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=5)
        if resp.status_code != 200:
            print("获取状态失败")
            time.sleep(10)
            continue
        
        task = resp.json()
        status = task.get("status", "unknown")
        elapsed = int(time.time() - start_time)
        
        print(f"第{elapsed}秒: 状态={status}")
        
        # 获取Agent状态
        agents_resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}/agents", timeout=5)
        if agents_resp.status_code == 200:
            agents = agents_resp.json()
            for agent, data in agents.items():
                if data.get("progress_percent", 0) > 0:
                    print(f"  {agent}: {data.get('progress_percent')}% - {data.get('message', '')}")
        
        # 检查是否完成
        if status in ["completed", "failed"]:
            print(f"\n任务{status}!")
            if status == "completed":
                print("✅ 测试成功完成！")
                print(f"任务ID: {task_id}")
                print(f"网页界面: http://127.0.0.1:9000")
                
                # 检查审核日志
                try:
                    files_resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}/files", timeout=5)
                    if files_resp.status_code == 200:
                        files = files_resp.json()
                        audit_files = [f for f in files if "audit" in f]
                        if audit_files:
                            print(f"审核文件: {', '.join(audit_files[:3])}")
                except:
                    pass
            else:
                print("❌ 任务失败")
                if "test_mode_reset_reason" in task:
                    print(f"失败原因: {task['test_mode_reset_reason']}")
            break
        
        time.sleep(15)
        
    except KeyboardInterrupt:
        print("\n监控被中断")
        break
    except Exception as e:
        print(f"监控错误: {e}")
        time.sleep(15)

if time.time() - start_time >= timeout:
    print("\n⏰ 监控超时（5分钟）")

print("\n" + "=" * 60)
print("测试完成")
print("=" * 60)