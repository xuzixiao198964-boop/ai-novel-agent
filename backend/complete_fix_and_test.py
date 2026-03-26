#!/usr/bin/env python3
"""
完整修复和测试循环
1. 修复所有问题
2. 部署到服务器
3. 运行测试验证
4. 重复直到成功
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

def execute_command(ssh, command):
    """执行SSH命令"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    return output, error

def check_server():
    """检查服务器状态"""
    try:
        resp = requests.get(f"http://{hostname}:9000/api/health", timeout=5)
        return resp.status_code == 200
    except:
        return False

def deploy_fix(ssh):
    """部署所有修复到服务器"""
    print("\n[部署修复]")
    
    # 1. 备份所有文件
    print("1. 备份文件...")
    files_to_backup = [
        "app/core/pipeline.py",
        "app/core/llm.py", 
        "app/agents/planner.py",
        ".env"
    ]
    
    for file in files_to_backup:
        execute_command(ssh, f"cd {project_path}/backend && cp {file} {file}.backup.{int(time.time())}")
    
    # 2. 上传修复后的pipeline.py（从本地）
    print("2. 上传pipeline.py修复...")
    with open("app/core/pipeline.py", "r", encoding="utf-8") as f:
        pipeline_content = f.read()
    
    sftp = ssh.open_sftp()
    with sftp.file(f"{project_path}/backend/app/core/pipeline.py", "w") as f:
        f.write(pipeline_content)
    sftp.close()
    
    # 3. 上传修复后的planner.py
    print("3. 上传planner.py修复...")
    with open("app/agents/planner.py", "r", encoding="utf-8") as f:
        planner_content = f.read()
    
    sftp = ssh.open_sftp()
    with sftp.file(f"{project_path}/backend/app/agents/planner.py", "w") as f:
        f.write(planner_content)
    sftp.close()
    
    # 4. 上传正确的.env
    print("4. 配置.env...")
    env_content = '''# DeepSeek API 配置
MOCK_LLM=0
LLM_API_BASE=https://api.deepseek.com
LLM_API_KEY=sk-7bfa809eeac74e168ee642d4e71b0958
LLM_MODEL=deepseek-chat

# 限速配置
AGENT_INTERVAL_SECONDS=2.0
STEP_INTERVAL_SECONDS=0.5

# 小说规模配置
TOTAL_CHAPTERS=0
MAX_CHAPTERS_TO_WRITE=0
WORDS_PER_CHAPTER=3000
'''
    execute_command(ssh, f"echo '{env_content}' > {project_path}/backend/.env")
    
    print("[OK] 所有修复已部署")

def restart_server(ssh):
    """重启服务器"""
    print("\n[重启服务器]")
    
    execute_command(ssh, "pkill -f 'python.*app.main'")
    execute_command(ssh, "pkill -f uvicorn")
    execute_command(ssh, "sleep 2")
    
    start_cmd = f"cd {project_path}/backend && nohup /opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 > server.log 2>&1 &"
    execute_command(ssh, start_cmd)
    
    # 等待启动
    print("等待服务器启动...")
    time.sleep(5)
    
    if check_server():
        print("[OK] 服务器启动成功")
        return True
    else:
        print("[ERROR] 服务器启动失败")
        return False

def run_test():
    """运行测试任务"""
    print("\n[运行测试]")
    
    try:
        # 1. 设置测试模式为6章（先小规模测试）
        print("1. 设置6章测试模式...")
        resp = requests.post(
            f"http://{hostname}:9000/api/run-mode",
            json={"mode": "test", "test_chapters": 6},
            timeout=10
        )
        print(f"设置结果: {resp.status_code} - {resp.json()}")
        
        # 2. 创建测试任务
        print("2. 创建测试任务...")
        task_name = f"修复验证测试-{datetime.now().strftime('%H%M%S')}"
        resp = requests.post(
            f"http://{hostname}:9000/api/tasks",
            json={"name": task_name},
            timeout=10
        )
        task_id = resp.json()["task_id"]
        print(f"任务ID: {task_id}")
        
        # 3. 启动任务
        print("3. 启动任务...")
        resp = requests.post(
            f"http://{hostname}:9000/api/tasks/{task_id}/start",
            timeout=10
        )
        print(f"启动结果: {resp.status_code}")
        
        return task_id
        
    except Exception as e:
        print(f"[ERROR] 运行测试失败: {e}")
        return None

def monitor_test(task_id, timeout_minutes=10):
    """监控测试任务"""
    print(f"\n[监控任务 {task_id}]")
    
    start_time = time.time()
    timeout = timeout_minutes * 60
    
    while time.time() - start_time < timeout:
        try:
            resp = requests.get(f"http://{hostname}:9000/api/tasks/{task_id}", timeout=5)
            if resp.status_code == 200:
                task = resp.json()
                status = task.get("status")
                elapsed = int(time.time() - start_time)
                
                print(f"第{elapsed}秒: 状态={status}")
                
                if status == "completed":
                    print("[SUCCESS] 测试成功完成！")
                    return True, "completed"
                elif status == "failed":
                    reason = task.get("test_mode_reset_reason", "未知原因")
                    print(f"[FAILURE] 测试失败: {reason}")
                    return False, reason
                
            time.sleep(30)
            
        except Exception as e:
            print(f"[ERROR] 监控错误: {e}")
            time.sleep(30)
    
    print(f"[TIMEOUT] 监控超时 ({timeout_minutes}分钟)")
    return False, "timeout"

def analyze_failure(ssh, task_id, reason):
    """分析失败原因"""
    print(f"\n[分析失败原因: {reason}]")
    
    # 检查日志
    output, _ = execute_command(ssh, f"tail -n 100 {project_path}/backend/server.log | grep -i 'error\\|exception\\|failed\\|json' | tail -20")
    if output:
        print(f"错误日志:\n{output}")
    
    # 检查任务文件
    output, _ = execute_command(ssh, f"find {project_path}/backend/data/tasks/{task_id} -name '*.txt' -o -name '*.json' | head -5")
    print(f"任务文件:\n{output}")
    
    # 根据原因返回需要修复的问题类型
    if "JSON" in reason or "json" in reason.lower():
        return "json_parse"
    elif "审核" in reason or "大纲" in reason:
        return "audit"
    elif "回退" in reason:
        return "rollback"
    else:
        return "unknown"

def main():
    """主循环：修复->部署->测试->分析->重复"""
    print("智能审核机制 - 完整修复验证循环")
    print("=" * 60)
    
    cycle = 0
    max_cycles = 10  # 最多尝试10次
    
    while cycle < max_cycles:
        cycle += 1
        print(f"\n{'='*60}")
        print(f"循环 {cycle}/{max_cycles}")
        print(f"{'='*60}")
        
        try:
            # 1. 连接服务器
            print("\n[连接服务器]")
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(hostname, port, username, password, timeout=10)
            print("[OK] 连接成功")
            
            # 2. 部署修复
            deploy_fix(ssh)
            
            # 3. 重启服务器
            if not restart_server(ssh):
                ssh.close()
                time.sleep(10)
                continue
            
            # 4. 运行测试
            task_id = run_test()
            if not task_id:
                ssh.close()
                time.sleep(10)
                continue
            
            # 5. 监控测试
            success, reason = monitor_test(task_id, timeout_minutes=15)
            
            if success:
                print("\n" + "="*60)
                print("[🎉 完全成功！] 智能审核机制验证通过！")
                print("="*60)
                ssh.close()
                return True
            else:
                # 6. 分析失败
                problem_type = analyze_failure(ssh, task_id, reason)
                print(f"[分析结果] 问题类型: {problem_type}")
                
                # 7. 根据问题类型进行针对性修复
                if problem_type == "json_parse":
                    print("[修复] 需要增强JSON解析...")
                    # 这里可以添加特定的JSON解析修复
                elif problem_type == "audit":
                    print("[修复] 需要调整审核逻辑...")
                    # 这里可以添加审核逻辑修复
                elif problem_type == "rollback":
                    print("[修复] 需要彻底禁用回退机制...")
                    # 确保pipeline.py中的回退逻辑完全禁用
                    output, _ = execute_command(ssh, f"grep -n '测试流程失败，回退到' {project_path}/backend/app/core/pipeline.py")
                    if output:
                        print(f"[警告] 发现回退代码，需要修复:\n{output}")
            
            ssh.close()
            
            # 等待下一轮
            print(f"\n等待5秒后开始下一轮...")
            time.sleep(5)
            
        except Exception as e:
            print(f"[ERROR] 循环失败: {e}")
            time.sleep(10)
    
    print("\n" + "="*60)
    print("[失败] 达到最大尝试次数，问题仍未解决")
    print("="*60)
    return False

if __name__ == "__main__":
    try:
        success = main()
        exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n[中断] 用户中断")
        exit(1)
    except Exception as e:
        print(f"[错误] 程序异常: {e}")
        exit(1)