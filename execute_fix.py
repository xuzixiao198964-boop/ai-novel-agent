import paramiko
import sys
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_ssh_command(client, cmd, description):
    """执行SSH命令并打印结果"""
    print(f"\n{description}:")
    print(f"  执行: {cmd}")
    
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='replace').strip()
        error = stderr.read().decode('utf-8', errors='replace').strip()
        
        if exit_status == 0:
            if output:
                print(f"  ✅ 输出: {output[:200]}")
            return True, output
        else:
            print(f"  ❌ 失败 (exit {exit_status}): {error[:200]}")
            return False, error
    except Exception as e:
        print(f"  ❌ 执行异常: {e}")
        return False, str(e)

def main():
    # 服务器信息
    HOST = "104.244.90.202"
    USER = "root"
    PASSWORD = "v9wSxMxg92dp"
    PORT = 22
    
    print("=== 执行裸机服务修复 ===")
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
        
        print("✅ 已连接到服务器")
        
        # 1. 清理冲突进程
        print("\n1. 清理冲突进程...")
        
        # 查找并杀死nohup进程
        _, output = run_ssh_command(client,
            "ps aux | grep 'nohup.*uvicorn.*9000' | grep -v grep",
            "查找nohup进程")
        
        if output:
            import re
            lines = output.split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        run_ssh_command(client,
                            f"kill -9 {pid}",
                            f"杀死nohup进程 {pid}")
        
        # 2. 重启服务
        print("\n2. 重启systemd服务...")
        run_ssh_command(client,
            "systemctl restart ai-novel-agent.service",
            "重启服务")
        
        time.sleep(3)
        
        # 3. 检查状态
        print("\n3. 检查服务状态...")
        run_ssh_command(client,
            "systemctl status ai-novel-agent.service --no-pager | head -5",
            "服务状态")
        
        run_ssh_command(client,
            "ps aux | grep 'uvicorn.*9000' | grep -v grep",
            "进程状态")
        
        # 4. 测试API
        print("\n4. 测试API...")
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/health",
            "健康检查")
        
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/config",
            "配置检查")
        
        client.close()
        
        print("\n" + "="*60)
        print("✅ 修复完成！")
        print("服务地址: http://104.244.90.202:9000")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")

if __name__ == "__main__":
    main()