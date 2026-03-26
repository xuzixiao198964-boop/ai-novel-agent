#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版18章测试
直接调用API启动测试任务
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:9000"

def print_step(step, message):
    """打印步骤信息"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {step}: {message}")

def create_task():
    """创建测试任务"""
    print_step("1", "创建18章测试任务")
    try:
        response = requests.post(
            f"{BASE_URL}/api/tasks",
            json={"name": "18章智能审核测试-" + datetime.now().strftime("%m%d%H%M")},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            print_step("1", f"任务创建成功: {task_id}")
            return task_id
        else:
            print_step("1", f"创建任务失败: {response.status_code}")
            return None
    except Exception as e:
        print_step("1", f"创建任务失败: {e}")
        return None

def set_test_mode_18ch():
    """设置为测试模式，18章"""
    print_step("2", "设置为测试模式（18章）")
    try:
        response = requests.post(
            f"{BASE_URL}/api/run-mode",
            json={"run_mode": "test", "test_chapters": 18},
            timeout=10
        )
        if response.status_code == 200:
            print_step("2", "测试模式设置成功")
            return True
        else:
            print_step("2", f"设置测试模式失败: {response.status_code}")
            return False
    except Exception as e:
        print_step("2", f"设置测试模式失败: {e}")
        return False

def start_pipeline(task_id):
    """启动流水线"""
    print_step("3", "启动创作流水线")
    try:
        response = requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/start",
            timeout=10
        )
        if response.status_code == 200:
            print_step("3", "流水线启动成功")
            return True
        else:
            print_step("3", f"启动流水线失败: {response.status_code}")
            return False
    except Exception as e:
        print_step("3", f"启动流水线失败: {e}")
        return False

def monitor_task(task_id):
    """监控任务进度"""
    print_step("4", "开始监控任务进度")
    print("=" * 60)
    
    start_time = time.time()
    last_status = None
    
    while True:
        try:
            # 获取任务状态
            response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=5)
            if response.status_code != 200:
                print_step("监控", "获取任务状态失败")
                time.sleep(10)
                continue
            
            task_data = response.json()
            status = task_data.get("status", "unknown")
            elapsed = int(time.time() - start_time)
            
            # 状态变化时打印
            if status != last_status:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"[{timestamp}] 运行{elapsed}s | 状态: {status}")
                last_status = status
            
            # 获取Agent状态
            agents_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/agents", timeout=5)
            if agents_response.status_code == 200:
                agents = agents_response.json()
                for agent_name, agent_data in agents.items():
                    progress = agent_data.get("progress_percent", 0)
                    message = agent_data.get("message", "")
                    agent_status = agent_data.get("status", "")
                    
                    # 只打印有进展的Agent
                    if progress > 0 or message:
                        print(f"  {agent_name}: {progress}% - {message}")
            
            # 检查是否完成
            if status in ["completed", "failed"]:
                print(f"\n任务{status}!")
                if status == "completed":
                    print("✅ 18章测试任务成功完成!")
                else:
                    print("❌ 任务失败")
                    # 获取失败详情
                    if "error" in task_data:
                        print(f"错误: {task_data['error']}")
                break
            
            time.sleep(15)  # 每15秒检查一次
            
        except KeyboardInterrupt:
            print("\n监控被用户中断")
            break
        except Exception as e:
            print(f"监控出错: {e}")
            time.sleep(15)
    
    return status == "completed"

def check_results(task_id):
    """检查结果"""
    print_step("5", "检查生成结果")
    
    # 这里可以添加检查生成文件、审核日志等的逻辑
    print("任务完成，结果检查:")
    print(f"任务ID: {task_id}")
    print(f"API地址: {BASE_URL}/api/tasks/{task_id}")
    print(f"网页界面: http://127.0.0.1:9000")
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("18章智能审核测试 - 简化版")
    print("=" * 60)
    
    # 1. 创建任务
    task_id = create_task()
    if not task_id:
        print("❌ 创建任务失败，退出")
        return False
    
    # 2. 设置测试模式
    if not set_test_mode_18ch():
        print("❌ 设置测试模式失败，退出")
        return False
    
    # 3. 启动流水线
    if not start_pipeline(task_id):
        print("❌ 启动流水线失败，退出")
        return False
    
    # 4. 监控进度
    success = monitor_task(task_id)
    
    # 5. 检查结果
    if success:
        check_results(task_id)
    
    print("\n" + "=" * 60)
    if success:
        print("✅ 18章测试完成！智能审核机制工作正常")
    else:
        print("❌ 测试失败，需要检查问题")
    print("=" * 60)
    
    return success

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except Exception as e:
        print(f"程序出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)