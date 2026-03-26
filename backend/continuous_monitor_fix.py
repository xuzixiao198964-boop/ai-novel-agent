#!/usr/bin/env python3
"""
持续监控、修复、验证循环
"""

import paramiko
import time
import requests
from datetime import datetime

hostname = "104.244.90.202"
port = 22
username = "root"
password = "v9wSxMxg92dp"
project_path = "/opt/ai-novel-agent"

def execute_ssh_command(ssh, command):
    """执行SSH命令"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    return output, error

def check_server_health():
    """检查服务器健康状态"""
    try:
        resp = requests.get(f"http://{hostname}:9000/api/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

def check_task_progress(task_id):
    """检查任务进度"""
    try:
        resp = requests.get(f"http://{hostname}:9000/api/tasks/{task_id}", timeout=5)
        if resp.status_code == 200:
            task = resp.json()
            return task.get("status"), task.get("updated_at"), task.get("genre_type")
    except:
        pass
    return None, None, None

def monitor_and_fix():
    """监控和修复循环"""
    print("持续监控与修复循环")
    print("=" * 60)
    
    cycle = 0
    last_fix_time = time.time()
    
    while True:
        cycle += 1
        print(f"\n[循环 {cycle}] {datetime.now().strftime('%H:%M:%S')}")
        print("-" * 40)
        
        # 1. 检查服务器健康
        if not check_server_health():
            print("[ERROR] 服务器不可用，尝试重启...")
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname, port, username, password, timeout=10)
                
                execute_ssh_command(ssh, "pkill -f 'python.*app.main'")
                execute_ssh_command(ssh, "pkill -f uvicorn")
                execute_ssh_command(ssh, "sleep 2")
                
                start_cmd = f"cd {project_path}/backend && nohup /opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 > server.log 2>&1 &"
                execute_ssh_command(ssh, start_cmd)
                
                ssh.close()
                print("[OK] 服务器已重启")
                time.sleep(10)
                continue
            except Exception as e:
                print(f"[ERROR] 重启失败: {e}")
                time.sleep(30)
                continue
        
        # 2. 检查任务状态
        task_id = "7b264f95"  # 当前测试任务
        status, updated_at, genre_type = check_task_progress(task_id)
        
        if status:
            print(f"任务 {task_id}: 状态={status}, 更新时间={updated_at}, 类型={genre_type}")
            
            # 检查是否卡住
            if status == "running" and updated_at:
                try:
                    # 解析时间
                    from datetime import datetime as dt
                    update_time = dt.fromisoformat(updated_at.replace('Z', '+00:00'))
                    now = dt.now(update_time.tzinfo) if update_time.tzinfo else dt.now()
                    minutes_since_update = (now - update_time).total_seconds() / 60
                    
                    if minutes_since_update > 10:  # 10分钟无更新视为卡住
                        print(f"[WARN] 任务已卡住 {minutes_since_update:.1f} 分钟")
                        
                        # 检查日志中的错误
                        try:
                            ssh = paramiko.SSHClient()
                            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                            ssh.connect(hostname, port, username, password, timeout=10)
                            
                            # 检查错误日志
                            logs, _ = execute_ssh_command(ssh, f"tail -n 50 {project_path}/backend/server.log | grep -i 'error\\|exception\\|json\\|failed'")
                            if logs:
                                print(f"[DEBUG] 发现错误日志:\n{logs[:500]}")
                            
                            # 检查审核文件
                            review_files, _ = execute_ssh_command(ssh, f"find {project_path}/backend/data/tasks/{task_id} -name '*审核*' -type f | head -3")
                            for file in review_files.split('\\n'):
                                if file:
                                    content, _ = execute_ssh_command(ssh, f"tail -n 10 {file}")
                                    print(f"[DEBUG] 审核文件 {file}: {content}")
                            
                            ssh.close()
                            
                        except Exception as e:
                            print(f"[ERROR] 检查日志失败: {e}")
                except Exception as e:
                    print(f"[ERROR] 解析时间失败: {e}")
            
            # 任务完成或失败
            if status in ["completed", "failed"]:
                print(f"[INFO] 任务{status}!")
                if status == "completed":
                    print("[SUCCESS] 🎉 18章测试成功完成！智能审核机制验证通过！")
                    return True
                else:
                    print("[FAILURE] 任务失败，需要分析原因")
                    # 获取失败详情
                    try:
                        resp = requests.get(f"http://{hostname}:9000/api/tasks/{task_id}", timeout=5)
                        task = resp.json()
                        print(f"失败原因: {task.get('test_mode_reset_reason', '未知')}")
                    except:
                        pass
                    return False
        else:
            print("[WARN] 无法获取任务状态")
        
        # 3. 定期检查日志（每3个循环检查一次）
        if cycle % 3 == 0:
            try:
                ssh = paramiko.SSHClient()
                ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
                ssh.connect(hostname, port, username, password, timeout=10)
                
                # 检查最新错误
                errors, _ = execute_ssh_command(ssh, f"tail -n 100 {project_path}/backend/server.log | grep -i 'json\\|parse\\|decode\\|syntax' | tail -5")
                if errors:
                    print(f"[DEBUG] JSON相关错误:\n{errors}")
                
                # 检查审核进度
                planner_logs, _ = execute_ssh_command(ssh, f"tail -n 50 {project_path}/backend/server.log | grep -i 'planner\\|策划\\|大纲\\|审核' | tail -5")
                if planner_logs:
                    print(f"[DEBUG] 策划相关日志:\n{planner_logs}")
                
                ssh.close()
                
            except Exception as e:
                print(f"[ERROR] 检查日志失败: {e}")
        
        # 4. 定期应用修复（每10分钟一次）
        if time.time() - last_fix_time > 600:  # 10分钟
            print("[INFO] 执行定期维护检查...")
            last_fix_time = time.time()
            
            # 这里可以添加定期修复逻辑
            # 例如：检查配置文件、重启服务等
        
        # 等待下一轮检查
        time.sleep(60)  # 1分钟检查一次

def main():
    """主函数"""
    print("智能审核机制 - 持续监控与修复")
    print("=" * 60)
    print("目标: 确保18章测试任务成功完成")
    print("策略: 监控 -> 发现问题 -> 修复 -> 验证")
    print("=" * 60)
    
    try:
        success = monitor_and_fix()
        if success:
            print("\n" + "=" * 60)
            print("[SUCCESS] 任务完成！智能审核机制验证通过！")
            print("=" * 60)
        else:
            print("\n" + "=" * 60)
            print("[FAILURE] 任务失败，需要进一步分析")
            print("=" * 60)
    except KeyboardInterrupt:
        print("\n[INFO] 监控被用户中断")
    except Exception as e:
        print(f"[ERROR] 监控失败: {e}")

if __name__ == "__main__":
    main()