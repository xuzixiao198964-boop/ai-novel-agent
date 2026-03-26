import paramiko
import sys

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def quick_check():
    # 服务器信息
    HOST = "104.244.90.202"
    USER = "root"
    PASSWORD = "v9wSxMxg92dp"
    PORT = 22
    
    print("=== 快速检查任务状态 ===")
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
        
        print("✅ 已连接到服务器")
        
        # 1. 查看所有任务
        print("\n1. 查看所有任务:")
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/tasks",
            "任务列表")
        
        # 2. 查看最新日志
        print("\n2. 查看最新日志:")
        run_ssh_command(client,
            "journalctl -u ai-novel-agent.service -n 20 --no-pager | grep -E '(error|Error|ERROR|fail|Fail|FAIL|parse_json|构建风格|风格解析)' || echo '无相关错误'",
            "错误日志")
        
        # 3. 检查 parse_json 函数
        print("\n3. 检查 parse_json 函数:")
        run_ssh_command(client,
            "grep -n 'def parse_json' /opt/ai-novel-agent/backend/app/core/llm.py",
            "parse_json 函数定义")
        
        # 4. 检查 style.py 中的调用
        print("\n4. 检查 style.py:")
        run_ssh_command(client,
            "grep -n 'parse_json' /opt/ai-novel-agent/backend/app/agents/style.py",
            "style.py 中的 parse_json 调用")
        
        # 5. 查看 style.py 内容
        print("\n5. 查看 style.py 相关代码:")
        run_ssh_command(client,
            "grep -B 10 -A 10 'parse_json' /opt/ai-novel-agent/backend/app/agents/style.py",
            "style.py 上下文")
        
        # 6. 测试直接修复
        print("\n6. 测试直接修复（如果需要）:")
        
        # 查看 style.py 的导入部分
        run_ssh_command(client,
            "head -30 /opt/ai-novel-agent/backend/app/agents/style.py",
            "style.py 开头")
        
        client.close()
        
        print("\n" + "="*60)
        print("检查完成")
        
    except Exception as e:
        print(f"❌ 检查失败: {e}")

def run_ssh_command(client, cmd, description):
    """执行SSH命令"""
    print(f"\n{description}:")
    print(f"  执行: {cmd}")
    
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=10)
        output = stdout.read().decode('utf-8', errors='replace').strip()
        if output:
            print(f"  {output[:500]}")
    except:
        pass

if __name__ == "__main__":
    quick_check()