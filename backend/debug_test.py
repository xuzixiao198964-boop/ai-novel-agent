#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调试测试：运行3章测试，查看审核机制是否工作
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:9000"

def test_small():
    """运行小规模测试"""
    print("=" * 60)
    print("调试测试：3章小规模测试")
    print("=" * 60)
    
    # 1. 设置测试模式为3章
    print("1. 设置测试模式为3章")
    resp = requests.post(
        f"{BASE_URL}/api/run-mode",
        json={"mode": "test", "test_chapters": 3},
        timeout=10
    )
    print(f"响应: {resp.status_code}, {resp.json()}")
    
    # 2. 创建任务
    print("\n2. 创建测试任务")
    resp = requests.post(
        f"{BASE_URL}/api/tasks",
        json={"name": "3章调试测试"},
        timeout=10
    )
    task_id = resp.json()["task_id"]
    print(f"任务ID: {task_id}")
    
    # 3. 启动任务
    print("\n3. 启动任务")
    resp = requests.post(
        f"{BASE_URL}/api/tasks/{task_id}/start",
        timeout=10
    )
    print(f"启动响应: {resp.status_code}")
    
    # 4. 简单监控
    print("\n4. 监控进度（30秒）")
    for i in range(6):  # 监控30秒
        time.sleep(5)
        resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=5)
        task = resp.json()
        status = task.get("status", "unknown")
        print(f"  第{i*5}秒: 状态={status}")
        
        if status in ["completed", "failed"]:
            print(f"  任务{status}!")
            break
    
    # 5. 检查Agent状态
    print("\n5. 检查Agent状态")
    resp = requests.get(f"{BASE_URL}/api/tasks/{task_id}/agents", timeout=5)
    if resp.status_code == 200:
        agents = resp.json()
        for agent, data in agents.items():
            print(f"  {agent}: {data.get('status')} - {data.get('message')}")
    
    print("\n" + "=" * 60)
    print("调试完成")
    return task_id

def check_audit_config():
    """检查审核配置"""
    print("\n检查审核配置...")
    try:
        # 尝试导入审核配置
        import sys
        sys.path.insert(0, '.')
        from app.core.audit_config import audit_config
        
        print(f"最大重试次数: {audit_config.max_retries}")
        print(f"批量大小: {audit_config.batch_size}")
        print(f"分数阈值: {audit_config.score_thresholds}")
        
        # 测试should_continue函数
        test_data = {
            "scores": {"overall": 75},
            "logic_issues": [],
            "ooc_issues": [],
            "coherence_issues": ["轻微问题"],
            "outline_violations": [],
            "plot_hole_issues": []
        }
        
        result, reason = audit_config.should_continue(test_data, 0, [])
        print(f"测试should_continue: {result} - {reason}")
        
        return True
    except Exception as e:
        print(f"检查审核配置失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("开始调试智能审核机制...")
    
    # 检查配置
    config_ok = check_audit_config()
    
    if config_ok:
        print("\n配置检查通过，开始运行测试...")
        task_id = test_small()
        
        print(f"\n测试任务ID: {task_id}")
        print(f"网页界面: http://127.0.0.1:9000")
        print(f"任务详情: {BASE_URL}/api/tasks/{task_id}")
    else:
        print("\n配置检查失败，需要修复代码")
        
    print("\n" + "=" * 60)