#!/usr/bin/env python3
"""
尝试停止卡住的任务 5760c4d1
"""

import requests
import time

SERVER_URL = "http://104.244.90.202:9000"
TASK_ID = "5760c4d1"

print(f"尝试停止卡住的任务 {TASK_ID}")
print("=" * 60)

# 方法1：尝试直接调用停止接口
print("1. 尝试调用停止接口...")
try:
    # 尝试不同的停止端点
    endpoints = [
        f"/api/tasks/{TASK_ID}/stop",
        f"/api/tasks/{TASK_ID}/cancel", 
        f"/api/tasks/{TASK_ID}/kill",
        f"/api/tasks/{TASK_ID}/abort"
    ]
    
    for endpoint in endpoints:
        try:
            print(f"尝试 {endpoint}...")
            resp = requests.post(SERVER_URL + endpoint, timeout=10)
            print(f"响应: {resp.status_code} - {resp.text[:100]}")
            if resp.status_code == 200:
                print(f"✅ 成功停止任务")
                break
        except Exception as e:
            print(f"失败: {e}")
            
except Exception as e:
    print(f"停止尝试失败: {e}")

# 方法2：检查任务状态
print("\n2. 检查任务状态...")
try:
    resp = requests.get(f"{SERVER_URL}/api/tasks/{TASK_ID}", timeout=10)
    if resp.status_code == 200:
        task = resp.json()
        print(f"任务状态: {task.get('status')}")
        print(f"最后更新: {task.get('updated_at')}")
        print(f"运行模式: {task.get('run_mode')}")
        print(f"测试章节: {task.get('test_mode_chapters')}")
        
        # 如果还是running，建议重启服务器
        if task.get('status') == 'running':
            print("\n⚠️ 任务仍在运行，建议重启服务器来停止所有任务")
    else:
        print(f"获取状态失败: {resp.status_code}")
except Exception as e:
    print(f"检查状态失败: {e}")

# 方法3：创建新任务测试系统是否响应
print("\n3. 测试系统响应...")
try:
    resp = requests.get(f"{SERVER_URL}/api/health", timeout=5)
    print(f"健康检查: {resp.status_code} - {resp.json()}")
    
    # 尝试创建一个小任务
    resp = requests.post(
        f"{SERVER_URL}/api/tasks",
        json={"name": "测试系统响应"},
        timeout=10
    )
    if resp.status_code == 200:
        print(f"✅ 系统响应正常，可以创建新任务")
    else:
        print(f"❌ 系统可能卡住: {resp.status_code}")
        
except Exception as e:
    print(f"测试失败: {e}")

print("\n" + "=" * 60)
print("建议操作:")
print("1. 如果任务无法停止，重启服务器: pkill -f uvicorn")
print("2. 应用修复文件 planner.py")
print("3. 重新启动服务器")
print("4. 运行新的18章测试")