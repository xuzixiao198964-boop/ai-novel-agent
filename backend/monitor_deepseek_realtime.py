#!/usr/bin/env python3
"""
实时监控 DeepSeek API 18章测试
"""

import requests
import time
from datetime import datetime

BASE_URL = "http://127.0.0.1:9000"
TASK_ID = "f5da247b"

def get_status():
    """获取任务状态"""
    try:
        resp = requests.get(f"{BASE_URL}/api/tasks/{TASK_ID}", timeout=10)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def get_agents():
    """获取Agent状态"""
    try:
        resp = requests.get(f"{BASE_URL}/api/tasks/{TASK_ID}/agents", timeout=5)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return {}

def format_time(seconds):
    """格式化时间"""
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    if hours > 0:
        return f"{hours}h{minutes}m{secs}s"
    elif minutes > 0:
        return f"{minutes}m{secs}s"
    else:
        return f"{secs}s"

def main():
    print("=" * 80)
    print("DeepSeek API 18章测试 - 实时监控")
    print(f"任务ID: {TASK_ID}")
    print("=" * 80)
    
    start_time = time.time()
    last_update = start_time
    agent_states = {}
    
    while True:
        try:
            # 获取状态
            task = get_status()
            if not task:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] 获取状态失败")
                time.sleep(10)
                continue
            
            status = task.get("status", "unknown")
            elapsed = int(time.time() - start_time)
            
            # 每30秒或状态变化时打印
            current_time = time.time()
            if current_time - last_update >= 30 or status != task.get("last_status", ""):
                print(f"\n[{datetime.now().strftime('%H:%M:%S')}] 运行{format_time(elapsed)} | 状态: {status}")
                
                # 显示任务信息
                if "genre_type" in task:
                    print(f"   小说类型: {task['genre_type']}")
                if "warning" in task and task["warning"]:
                    print(f"   警告: {task['warning']}")
                
                # 获取Agent状态
                agents = get_agents()
                if agents:
                    print("   Agent进度:")
                    # 按处理顺序显示
                    agent_order = ["TrendAgent", "StyleAgent", "PlannerAgent", "WriterAgent", 
                                  "PolishAgent", "AuditorAgent", "ScorerAgent", "ReviserAgent"]
                    
                    for agent in agent_order:
                        if agent in agents:
                            data = agents[agent]
                            progress = data.get("progress_percent", 0)
                            message = data.get("message", "")
                            agent_status = data.get("status", "")
                            
                            # 检查状态变化
                            prev_state = agent_states.get(agent, {})
                            if (progress != prev_state.get("progress") or 
                                message != prev_state.get("message") or
                                agent_status != prev_state.get("status")):
                                
                                status_symbol = "🟢" if agent_status == "completed" else "🟡" if agent_status == "running" else "⚪"
                                print(f"     {status_symbol} {agent}: {progress}% - {message}")
                                agent_states[agent] = {"progress": progress, "message": message, "status": agent_status}
                
                last_update = current_time
                task["last_status"] = status
            
            # 检查是否完成
            if status in ["completed", "failed"]:
                print(f"\n{'✅' if status == 'completed' else '❌'} 任务{status}!")
                print(f"总耗时: {format_time(elapsed)}")
                
                if status == "completed":
                    print("\n🎉 DeepSeek API 18章测试成功完成！")
                    print("智能审核机制验证通过！")
                    
                    # 显示关键信息
                    for key in ["platform_sync_ok", "test_mode_next_chapters", "genre_type"]:
                        if key in task:
                            print(f"   {key}: {task[key]}")
                else:
                    print("\n任务失败详情:")
                    for key in ["error", "test_mode_reset_reason", "warning"]:
                        if key in task and task[key]:
                            print(f"   {key}: {task[key]}")
                
                break
            
            time.sleep(10)  # 每10秒检查一次
            
        except KeyboardInterrupt:
            print("\n\n监控被用户中断")
            break
        except Exception as e:
            print(f"\n监控错误: {e}")
            time.sleep(30)
    
    # 最终总结
    print("\n" + "=" * 80)
    print("测试总结")
    print("=" * 80)
    
    if task:
        print(f"任务ID: {TASK_ID}")
        print(f"状态: {task.get('status')}")
        print(f"创建时间: {task.get('created_at')}")
        print(f"更新时间: {task.get('updated_at')}")
        print(f"测试章节: {task.get('test_mode_chapters')}")
    
    print("\n网页界面: http://127.0.0.1:9000")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序出错: {e}")
        import traceback
        traceback.print_exc()