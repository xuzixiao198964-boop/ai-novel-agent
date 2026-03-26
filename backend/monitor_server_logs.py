#!/usr/bin/env python3
"""
监听服务器日志，查找JSON解析错误
"""

import paramiko
import time
import re

hostname = "104.244.90.202"
port = 22
username = "root"
password = "v9wSxMxg92dp"
project_path = "/opt/ai-novel-agent"

def execute_command(ssh, command):
    """执行命令"""
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    return output, error

print("监听服务器日志 - 查找JSON解析错误")
print("=" * 60)

try:
    # 连接服务器
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password, timeout=10)
    print("[OK] 连接成功")
    
    # 获取当前日志
    print("\n获取当前服务器日志...")
    output, _ = execute_command(ssh, f"tail -n 100 {project_path}/backend/server.log")
    
    # 查找JSON相关错误
    print("\n分析日志中的JSON错误...")
    
    json_errors = []
    llm_errors = []
    planner_errors = []
    
    lines = output.split('\n')
    for i, line in enumerate(lines):
        line_lower = line.lower()
        
        # JSON相关错误
        if any(keyword in line_lower for keyword in ['json', 'parse', 'decode', 'syntax', 'invalid']):
            json_errors.append(f"行 {i}: {line}")
            # 显示上下文
            if i > 0:
                json_errors.append(f"  上文: {lines[i-1]}")
            if i < len(lines)-1:
                json_errors.append(f"  下文: {lines[i+1]}")
        
        # LLM/API错误
        if any(keyword in line_lower for keyword in ['llm', 'api', 'deepseek', 'openai', 'timeout', 'connection']):
            llm_errors.append(f"行 {i}: {line}")
        
        # Planner相关错误
        if any(keyword in line_lower for keyword in ['planner', '策划', '大纲', '审核', 'spine', 'outline']):
            planner_errors.append(f"行 {i}: {line}")
    
    # 输出结果
    if json_errors:
        print("\n[ERROR] 找到JSON解析错误:")
        for error in json_errors[:10]:  # 显示前10个
            print(error)
    else:
        print("\n[OK] 未发现JSON解析错误")
    
    if llm_errors:
        print("\n[WARN] LLM/API相关错误:")
        for error in llm_errors[:5]:
            print(error)
    
    if planner_errors:
        print("\n[INFO] Planner相关日志:")
        for error in planner_errors[:10]:
            print(error)
    
    # 实时监控
    print("\n" + "=" * 60)
    print("开始实时监控（按Ctrl+C停止）...")
    print("=" * 60)
    
    last_position = 0
    try:
        while True:
            # 获取日志文件大小
            size_output, _ = execute_command(ssh, f"wc -c {project_path}/backend/server.log | cut -d' ' -f1")
            try:
                current_size = int(size_output.strip())
            except:
                current_size = 0
            
            if current_size > last_position:
                # 读取新内容
                output, _ = execute_command(ssh, f"tail -c +{last_position} {project_path}/backend/server.log | tail -n 50")
                if output:
                    print(f"\n[{time.strftime('%H:%M:%S')}] 新日志:")
                    print("-" * 40)
                    
                    lines = output.split('\n')
                    for line in lines:
                        if any(keyword in line.lower() for keyword in ['error', 'exception', 'traceback', 'json', 'parse', 'failed']):
                            print(f"[ERROR] {line}")
                        elif any(keyword in line.lower() for keyword in ['planner', '策划', '审核', 'spine']):
                            print(f"[PLANNER] {line}")
                        elif 'INFO' in line:
                            # 只显示重要的INFO
                            if any(keyword in line for keyword in ['task', 'agent', 'chapter', '章']):
                                print(f"[INFO] {line}")
                    
                    # 检查特定错误
                    for line in lines:
                        if 'json' in line.lower() and ('error' in line.lower() or 'exception' in line.lower()):
                            print(f"\n[CRITICAL] 发现JSON错误: {line}")
                
                last_position = current_size
            
            # 检查任务状态
            output, _ = execute_command(ssh, "curl -s http://localhost:9000/api/tasks | python3 -c \"import sys,json; data=json.load(sys.stdin); tasks=[t for t in data.get('tasks',[]) if t.get('status') in ['running','failed']]; print(f'活跃任务: {len(tasks)}'); [print(f'  {t[\"task_id\"]}: {t[\"status\"]} - {t.get(\"name\",\"\")[:30]}...') for t in tasks]\" 2>/dev/null || echo '检查失败'")
            if output and '活跃任务' in output:
                print(f"\n📊 {output}")
            
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n监控停止")
    
    ssh.close()
    
except Exception as e:
    print(f"[ERROR] 错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n监听结束")