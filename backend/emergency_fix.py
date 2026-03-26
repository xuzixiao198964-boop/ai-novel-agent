#!/usr/bin/env python3
"""
紧急修复：检查并修复测试失败回退问题
"""

import paramiko
import time

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
    return output, error

print("紧急修复：测试失败回退问题")
print("=" * 60)

try:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(hostname, port, username, password, timeout=10)
    print("[OK] 连接成功")
    
    # 1. 检查pipeline.py中的回退逻辑
    print("\n1. 检查pipeline.py回退逻辑...")
    output, _ = execute_command(ssh, f"grep -n '测试流程失败，回退到' {project_path}/backend/app/core/pipeline.py")
    print(f"回退逻辑位置:\n{output}")
    
    # 查看具体代码
    if output:
        line_num = output.split(':')[0]
        output, _ = execute_command(ssh, f"sed -n '{int(line_num)-5},{int(line_num)+10}p' {project_path}/backend/app/core/pipeline.py")
        print(f"回退代码上下文:\n{output}")
    
    # 2. 检查是否有备份文件
    print("\n2. 检查备份文件...")
    output, _ = execute_command(ssh, f"ls -la {project_path}/backend/app/core/pipeline.py*")
    print(f"pipeline.py文件:\n{output}")
    
    # 3. 查看当前pipeline.py内容
    print("\n3. 查看当前pipeline.py关键部分...")
    # 查找test_mode_reset_reason相关代码
    output, _ = execute_command(ssh, f"grep -n 'test_mode_reset_reason\\|test_mode_next_chapters' {project_path}/backend/app/core/pipeline.py -B2 -A2")
    print(f"测试模式重置相关代码:\n{output}")
    
    # 4. 检查最近修改
    print("\n4. 检查文件修改时间...")
    output, _ = execute_command(ssh, f"stat {project_path}/backend/app/core/pipeline.py")
    print(f"文件状态:\n{output}")
    
    # 5. 查看服务器日志中的错误
    print("\n5. 查看服务器日志...")
    output, _ = execute_command(ssh, f"tail -n 50 {project_path}/backend/server.log | grep -i '失败\\|error\\|exception'")
    print(f"错误日志:\n{output}")
    
    # 6. 检查任务失败详情
    print("\n6. 检查最新失败任务...")
    output, _ = execute_command(ssh, f"cat {project_path}/backend/data/tasks/eb72bd66/meta.json 2>/dev/null || echo '任务文件不存在'")
    print(f"失败任务元数据:\n{output}")
    
    # 7. 修复pipeline.py
    print("\n7. 修复pipeline.py...")
    
    # 先备份
    execute_command(ssh, f"cp {project_path}/backend/app/core/pipeline.py {project_path}/backend/app/core/pipeline.py.backup.emergency")
    
    # 读取文件
    output, _ = execute_command(ssh, f"cat {project_path}/backend/app/core/pipeline.py")
    lines = output.split('\n')
    
    # 查找并修复回退逻辑
    fixed_lines = []
    for i, line in enumerate(lines):
        if '测试流程失败，回退到' in line and 'test_mode_next_chapters' in line:
            print(f"找到回退逻辑在第{i+1}行: {line}")
            # 修改为：失败时不回退，保持当前章节数
            if 'test_mode_next_chapters = 6' in line:
                # 改为保持当前章节数
                fixed_line = line.replace('test_mode_next_chapters = 6', 'test_mode_next_chapters = task_meta.get("test_mode_chapters", 6)')
                print(f"修改为: {fixed_line}")
                fixed_lines.append(fixed_line)
            else:
                fixed_lines.append(line)
        elif 'test_mode_reset_reason = ' in line and '测试流程失败，回退到' in lines[i-1] if i>0 else False:
            # 这是原因行，保持原样
            fixed_lines.append(line)
        else:
            fixed_lines.append(line)
    
    # 写回文件
    fixed_content = '\n'.join(fixed_lines)
    execute_command(ssh, f"echo '{fixed_content}' > {project_path}/backend/app/core/pipeline.py.fixed")
    execute_command(ssh, f"cp {project_path}/backend/app/core/pipeline.py.fixed {project_path}/backend/app/core/pipeline.py")
    
    print("[OK] pipeline.py已修复")
    
    # 8. 验证修复
    print("\n8. 验证修复...")
    output, _ = execute_command(ssh, f"grep -n 'test_mode_next_chapters = task_meta.get' {project_path}/backend/app/core/pipeline.py")
    print(f"验证结果:\n{output}")
    
    # 9. 重启服务器
    print("\n9. 重启服务器...")
    execute_command(ssh, "pkill -f 'python.*app.main'")
    execute_command(ssh, "pkill -f uvicorn")
    execute_command(ssh, "sleep 2")
    
    start_cmd = f"cd {project_path}/backend && nohup /opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 > server.log 2>&1 &"
    execute_command(ssh, start_cmd)
    
    # 10. 检查服务器状态
    print("\n10. 检查服务器状态...")
    execute_command(ssh, "sleep 5")
    output, _ = execute_command(ssh, "curl -s http://localhost:9000/api/health")
    print(f"健康检查: {output}")
    
    ssh.close()
    
    print("\n" + "=" * 60)
    print("[OK] 紧急修复完成")
    print("已修复测试失败回退逻辑")
    print("=" * 60)
    
except Exception as e:
    print(f"[ERROR] 错误: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()

print("\n修复完成")