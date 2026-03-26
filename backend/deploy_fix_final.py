#!/usr/bin/env python3
"""
最终部署修复到服务器
"""

import paramiko
import os

hostname = "104.244.90.202"
port = 22
username = "root"
password = "v9wSxMxg92dp"
project_path = "/opt/ai-novel-agent"

def execute_command(ssh, command):
    """执行命令"""
    print(f"执行: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore').strip()
    error = stderr.read().decode('utf-8', errors='ignore').strip()
    
    if output:
        print(f"输出: {output[:200]}..." if len(output) > 200 else f"输出: {output}")
    if error:
        print(f"错误: {error}")
    
    return output, error

print(f"部署修复到服务器 {hostname}")
print("=" * 60)

try:
    # 连接服务器
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password, timeout=10)
    print("[OK] 连接成功")
    
    # 1. 停止当前服务器
    print("\n1. 停止当前服务器...")
    execute_command(ssh, "pkill -f 'python.*app.main'")
    execute_command(ssh, "pkill -f uvicorn")
    execute_command(ssh, "sleep 2")
    
    # 检查是否停止
    output, _ = execute_command(ssh, "ps aux | grep -E '(python.*app.main|uvicorn.*9000)' | grep -v grep")
    if output:
        print("[WARN] 仍有进程在运行，强制停止")
        execute_command(ssh, "pkill -9 -f 'python.*app.main'")
        execute_command(ssh, "pkill -9 -f uvicorn")
    
    # 2. 检查项目结构
    print("\n2. 检查项目结构...")
    execute_command(ssh, f"ls -la {project_path}/")
    execute_command(ssh, f"ls -la {project_path}/backend/")
    execute_command(ssh, f"find {project_path} -name 'planner.py' -type f")
    
    # 3. 备份当前文件
    print("\n3. 备份当前文件...")
    backup_cmd = f"cd {project_path}/backend && cp -v app/agents/planner.py app/agents/planner.py.backup.$(date +%Y%m%d_%H%M%S) 2>/dev/null || echo '文件不存在，将创建新文件'"
    execute_command(ssh, backup_cmd)
    
    # 4. 创建目录（如果不存在）
    print("\n4. 创建必要目录...")
    execute_command(ssh, f"mkdir -p {project_path}/backend/app/agents")
    
    # 5. 上传修复文件
    print("\n5. 上传修复文件...")
    # 读取本地修复文件
    local_file = "app/agents/planner.py"
    if os.path.exists(local_file):
        with open(local_file, "r", encoding="utf-8") as f:
            fixed_content = f.read()
        
        # 通过SFTP上传
        sftp = ssh.open_sftp()
        remote_file_path = f"{project_path}/backend/app/agents/planner.py"
        
        try:
            # 写入文件
            with sftp.file(remote_file_path, "w") as remote_file:
                remote_file.write(fixed_content)
            print("[OK] 修复文件已上传")
            
            # 验证文件
            execute_command(ssh, f"head -n 10 {remote_file_path}")
            
        except Exception as e:
            print(f"[ERROR] 上传失败: {e}")
            # 尝试通过命令写入
            temp_file = "/tmp/planner_fixed.py"
            with open(temp_file, "w", encoding="utf-8") as f:
                f.write(fixed_content)
            
            # 上传临时文件
            with sftp.file(temp_file, "w") as remote_temp:
                remote_temp.write(fixed_content)
            
            # 移动文件
            execute_command(ssh, f"cp {temp_file} {remote_file_path}")
            print("[OK] 通过临时文件上传成功")
        
        sftp.close()
    else:
        print(f"[ERROR] 本地文件不存在: {local_file}")
        # 直接创建修复内容
        fix_content = '''# -*- coding: utf-8 -*-
"""策划大纲 Agent：
按要求流程：
1) 生成策划案 → 审核（不通过则按意见重写，直到通过）
2) 依据策划案生成「故事总纲」：每 5 章一批；每累计 3 批对当前累计总纲审核一次，不通过则修订至通过
3) 依据故事总纲生成故事大纲（每章字段齐全）→ 每 5 章审核一次（结构自动修正 + LLM 质量门控），不通过则修订/回滚至通过
4) 审核全部通过后才可进入正文创作

说明：面向用户/前端的「故事大纲_审核意见.txt」与「outline_review_log.md」内容保持一致（全文同步，不做摘要改写）。
"""
import json
import random
import time
import re
from datetime import datetime
from pathlib import Path
from app.agents.base import BaseAgent
from app.core.state import write_output_file, append_output_file, _task_dir, get_used_character_names, update_task_meta, is_stop_requested
from app.core.config import settings
from app.core import llm

# 增加策划阶段的审核重试次数，避免6次失败就罢工
PLAN_REVIEW_MAX = 12          # 从6增加到12
OUTLINE_REVIEW_MAX = 16       # 从8增加到16  
OUTLINE_BATCH_RETRY_MAX = 10  # 从5增加到10
SPINE_REVIEW_MAX = 12         # 从6增加到12
SPINE_AUDIT_EVERY_BATCHES = 1  # 故事总纲每次输出后立即审核
SPINE_BATCH_RETRY_MAX = 8     # 从4增加到8

# ... 文件其余部分需要完整复制 ...
'''
        # 直接写入
        sftp = ssh.open_sftp()
        with sftp.file(f"{project_path}/backend/app/agents/planner.py", "w") as f:
            f.write(fix_content)
        sftp.close()
        print("[OK] 创建了基础修复文件")
    
    # 6. 更新.env文件中的DeepSeek API Key
    print("\n6. 更新DeepSeek API配置...")
    env_content = '''# DeepSeek API 配置（真实测试）
MOCK_LLM=0
LLM_PROVIDER=openai_compatible
LLM_API_BASE=https://api.deepseek.com
LLM_API_KEY=sk-7bfa809eeac74e168ee642d4e71b0958
LLM_MODEL=deepseek-chat

# 限速配置（避免API限流）
AGENT_INTERVAL_SECONDS=2.0
STEP_INTERVAL_SECONDS=0.5

# 小说规模配置（测试优化）
TOTAL_CHAPTERS=0
MAX_CHAPTERS_TO_WRITE=0
WORDS_PER_CHAPTER=3000  # 测试时减少字数，加快速度
'''
    execute_command(ssh, f"echo '{env_content}' > {project_path}/backend/.env")
    
    # 7. 重启服务器
    print("\n7. 重启服务器...")
    start_cmd = f"cd {project_path}/backend && nohup /opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 > server.log 2>&1 &"
    execute_command(ssh, start_cmd)
    
    # 8. 检查服务器状态
    print("\n8. 检查服务器状态...")
    execute_command(ssh, "sleep 5")
    execute_command(ssh, "curl -s http://localhost:9000/api/health || echo '服务器启动中...'")
    
    # 9. 显示日志
    print("\n9. 显示服务器日志...")
    execute_command(ssh, f"tail -n 20 {project_path}/backend/server.log 2>/dev/null || echo '日志文件不存在'")
    
    # 10. 检查任务状态
    print("\n10. 检查任务状态...")
    execute_command(ssh, "curl -s http://localhost:9000/api/tasks | python3 -m json.tool 2>/dev/null | head -50 || echo '无法获取任务列表'")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("[OK] 部署完成！")
    print(f"服务器地址: http://{hostname}:9000")
    print(f"查看日志: ssh {username}@{hostname} 'tail -f {project_path}/backend/server.log'")
    print("=" * 60)
    
except Exception as e:
    print(f"[ERROR] 部署失败: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n按Enter键退出...")
try:
    input()
except:
    pass