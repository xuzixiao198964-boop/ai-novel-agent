#!/usr/bin/env python3
"""
SSH连接到服务器执行命令
"""

import paramiko
import sys

# 服务器信息
hostname = "104.244.90.202"
port = 22
username = "root"
password = "v9wSxMxg92dp"

def execute_command(ssh, command):
    """执行命令并返回输出"""
    print(f"执行: {command}")
    stdin, stdout, stderr = ssh.exec_command(command)
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    if output:
        print(f"输出: {output.strip()}")
    if error:
        print(f"错误: {error.strip()}")
    
    return output, error

def main():
    print(f"连接到服务器 {hostname}:{port}")
    print("=" * 60)
    
    try:
        # 创建SSH客户端
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        # 连接服务器
        print("正在连接...")
        ssh.connect(hostname, port, username, password, timeout=10)
        print("[OK] 连接成功")
        
        # 1. 停止服务器
        print("\n1. 停止当前服务器...")
        execute_command(ssh, "pkill -f uvicorn")
        execute_command(ssh, "sleep 2")
        execute_command(ssh, "ps aux | grep uvicorn | grep -v grep")
        
        # 2. 查找项目路径
        print("\n2. 查找ai-novel-agent项目...")
        output, _ = execute_command(ssh, "find / -name 'ai-novel-agent' -type d 2>/dev/null | head -5")
        
        if not output.strip():
            # 尝试其他可能路径
            possible_paths = [
                "/root/ai-novel-agent",
                "/home/ai-novel-agent", 
                "/opt/ai-novel-agent",
                "/var/www/ai-novel-agent"
            ]
            
            for path in possible_paths:
                output, _ = execute_command(ssh, f"ls -la {path} 2>/dev/null || echo '不存在'")
                if "不存在" not in output:
                    project_path = path
                    break
            else:
                print("[ERROR] 找不到项目路径")
                project_path = input("请输入项目路径: ").strip()
        else:
            project_path = output.strip().split('\n')[0]
        
        print(f"项目路径: {project_path}")
        
        # 3. 备份当前文件
        print(f"\n3. 备份当前planner.py文件...")
        backup_cmd = f"cd {project_path}/backend && cp app/agents/planner.py app/agents/planner.py.backup.$(date +%Y%m%d_%H%M%S)"
        execute_command(ssh, backup_cmd)
        
        # 4. 上传修复文件
        print("\n4. 上传修复文件...")
        # 首先读取本地修复文件
        with open("app/agents/planner.py", "r", encoding="utf-8") as f:
            fixed_content = f.read()
        
        # 创建SFTP连接上传文件
        sftp = ssh.open_sftp()
        remote_path = f"{project_path}/backend/app/agents/planner.py"
        
        # 写入修复内容
        with sftp.file(remote_path, "w") as remote_file:
            remote_file.write(fixed_content)
        
        sftp.close()
        print("[OK] 修复文件已上传")
        
        # 5. 重启服务器
        print("\n5. 重启服务器...")
        start_cmd = f"cd {project_path}/backend && nohup uvicorn app.main:app --host 0.0.0.0 --port 9000 > server.log 2>&1 &"
        execute_command(ssh, start_cmd)
        
        # 6. 检查服务器状态
        print("\n6. 检查服务器状态...")
        execute_command(ssh, "sleep 3")
        execute_command(ssh, "curl -s http://localhost:9000/api/health || echo '服务器启动中...'")
        
        # 7. 显示日志
        print("\n7. 显示服务器日志...")
        execute_command(ssh, f"tail -n 10 {project_path}/backend/server.log 2>/dev/null || echo '日志文件不存在'")
        
        print("\n" + "=" * 60)
        print("[OK] 部署完成！")
        print(f"服务器地址: http://{hostname}:9000")
        print(f"查看实时日志: tail -f {project_path}/backend/server.log")
        
        # 关闭连接
        ssh.close()
        
    except paramiko.AuthenticationException:
        print("[ERROR] 认证失败，请检查用户名和密码")
    except paramiko.SSHException as e:
        print(f"[ERROR] SSH连接失败: {e}")
    except Exception as e:
        print(f"[ERROR] 错误: {type(e).__name__}: {e}")
    
    print("\n按Enter键退出...")
    input()

if __name__ == "__main__":
    main()