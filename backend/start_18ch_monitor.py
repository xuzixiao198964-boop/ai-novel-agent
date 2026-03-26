#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
启动并监控18章测试任务
"""

import requests
import time
import json
from datetime import datetime

BASE_URL = "http://127.0.0.1:9000"

def log(step, message):
    """记录日志"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] {step}: {message}")

def setup_test_mode():
    """设置测试模式为18章"""
    log("设置", "设置为测试模式（18章）")
    try:
        response = requests.post(
            f"{BASE_URL}/api/run-mode",
            json={"mode": "test", "test_chapters": 18},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            log("设置", f"成功 - 模式: {data.get('mode')}, 测试章节: {data.get('test_chapters')}")
            return True
        else:
            log("设置", f"失败 - 状态码: {response.status_code}, 响应: {response.text}")
            return False
    except Exception as e:
        log("设置", f"异常 - {e}")
        return False

def create_test_task():
    """创建测试任务"""
    log("任务", "创建18章测试任务")
    try:
        task_name = f"18章智能审核测试-{datetime.now().strftime('%m%d%H%M')}"
        response = requests.post(
            f"{BASE_URL}/api/tasks",
            json={"name": task_name},
            timeout=10
        )
        if response.status_code == 200:
            data = response.json()
            task_id = data.get("task_id")
            log("任务", f"创建成功 - ID: {task_id}")
            return task_id
        else:
            log("任务", f"创建失败 - 状态码: {response.status_code}")
            return None
    except Exception as e:
        log("任务", f"创建异常 - {e}")
        return None

def start_task_pipeline(task_id):
    """启动任务流水线"""
    log("启动", f"启动任务 {task_id} 的流水线")
    try:
        response = requests.post(
            f"{BASE_URL}/api/tasks/{task_id}/start",
            timeout=10
        )
        if response.status_code == 200:
            log("启动", "流水线启动成功")
            return True
        else:
            log("启动", f"启动失败 - 状态码: {response.status_code}, 响应: {response.text}")
            return False
    except Exception as e:
        log("启动", f"启动异常 - {e}")
        return False

def monitor_task(task_id):
    """监控任务进度"""
    log("监控", "开始监控任务进度")
    print("=" * 60)
    
    start_time = time.time()
    last_progress = {}
    last_status = None
    
    while True:
        try:
            # 获取任务状态
            task_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}", timeout=5)
            if task_response.status_code != 200:
                time.sleep(10)
                continue
            
            task_data = task_response.json()
            status = task_data.get("status", "unknown")
            elapsed = int(time.time() - start_time)
            
            # 获取Agent状态
            agents_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/agents", timeout=5)
            agents_data = agents_response.json() if agents_response.status_code == 200 else {}
            
            # 状态变化时打印
            if status != last_status:
                timestamp = datetime.now().strftime("%H:%M:%S")
                print(f"\n[{timestamp}] 运行{elapsed}秒 | 任务状态: {status}")
                last_status = status
            
            # 打印有进展的Agent
            for agent_name, agent_info in agents_data.items():
                progress = agent_info.get("progress_percent", 0)
                message = agent_info.get("message", "")
                
                # 只打印有变化或重要的Agent
                if (agent_name not in last_progress or 
                    last_progress[agent_name] != progress or
                    progress > 0):
                    if progress > 0 or message:
                        print(f"  {agent_name}: {progress}% - {message}")
                        last_progress[agent_name] = progress
            
            # 检查是否完成
            if status in ["completed", "failed"]:
                print(f"\n任务{status}!")
                if status == "completed":
                    print("✅ 18章测试任务成功完成!")
                else:
                    print("❌ 任务失败")
                    if "error" in task_data:
                        print(f"错误信息: {task_data['error']}")
                break
            
            time.sleep(15)  # 每15秒检查一次
            
        except KeyboardInterrupt:
            print("\n监控被用户中断")
            return "interrupted"
        except Exception as e:
            print(f"监控出错: {e}")
            time.sleep(15)
    
    return status

def check_audit_logs(task_id):
    """检查审核日志"""
    log("检查", "检查审核日志")
    try:
        # 尝试获取审核相关文件
        files_response = requests.get(f"{BASE_URL}/api/tasks/{task_id}/files", timeout=5)
        if files_response.status_code == 200:
            files = files_response.json()
            audit_files = [f for f in files if "audit" in f]
            if audit_files:
                log("检查", f"找到审核文件: {', '.join(audit_files)}")
            else:
                log("检查", "未找到审核文件")
    except Exception as e:
        log("检查", f"检查日志异常: {e}")

def main():
    """主函数"""
    print("=" * 60)
    print("18章智能审核测试 - 实时监控")
    print("=" * 60)
    
    # 1. 设置测试模式
    if not setup_test_mode():
        print("❌ 设置测试模式失败，退出")
        return False
    
    # 2. 创建任务
    task_id = create_test_task()
    if not task_id:
        print("❌ 创建任务失败，退出")
        return False
    
    # 3. 启动流水线
    if not start_task_pipeline(task_id):
        print("❌ 启动流水线失败，退出")
        return False
    
    # 4. 监控进度
    final_status = monitor_task(task_id)
    
    # 5. 检查结果
    if final_status == "completed":
        check_audit_logs(task_id)
        print("\n✅ 智能审核机制测试完成！")
        print(f"任务ID: {task_id}")
        print(f"网页界面: http://127.0.0.1:9000")
        return True
    elif final_status == "failed":
        print("\n❌ 测试失败，需要检查问题")
        print("建议检查:")
        print("1. 服务器日志")
        print("2. Agent错误信息")
        print("3. 审核配置是否正确")
        return False
    else:
        print("\n⚠️ 监控被中断")
        return False

if __name__ == "__main__":
    try:
        success = main()
        print("=" * 60)
        if success:
            print("测试完成！智能审核机制工作正常")
        else:
            print("测试失败，需要进一步调试")
        print("=" * 60)
        exit(0 if success else 1)
    except Exception as e:
        print(f"程序出错: {e}")
        import traceback
        traceback.print_exc()
        exit(1)