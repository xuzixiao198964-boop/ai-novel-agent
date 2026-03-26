import paramiko
import sys
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def run_ssh_command(client, cmd, description):
    """执行SSH命令"""
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

def final_fix():
    # 服务器信息
    HOST = "104.244.90.202"
    USER = "root"
    PASSWORD = "v9wSxMxg92dp"
    PORT = 22
    
    print("=== 最终修复：解决端口冲突和配置问题 ===")
    print("="*60)
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
        
        print("✅ 已连接到服务器")
        
        # 步骤1: 停止所有相关进程
        print("\n1. 停止所有相关进程")
        
        # 1.1 查找所有占用9000端口的进程
        _, output = run_ssh_command(client,
            "ps aux | grep -E '(9000|uvicorn.*ai-novel)' | grep -v grep",
            "查找所有相关进程")
        
        if output:
            lines = output.split('\n')
            for line in lines:
                if line.strip():
                    parts = line.split()
                    if len(parts) > 1:
                        pid = parts[1]
                        # 检查是否是我们要杀死的进程
                        if 'uvicorn' in line or '9000' in line:
                            run_ssh_command(client,
                                f"kill -9 {pid}",
                                f"杀死进程 {pid}")
        
        # 1.2 确认端口释放
        time.sleep(2)
        run_ssh_command(client,
            "ss -tlnp | grep :9000 || echo '✅ 端口9000已释放'",
            "检查端口释放")
        
        # 步骤2: 修复systemd服务配置
        print("\n2. 修复systemd服务配置")
        
        # 2.1 检查当前配置
        _, service_content = run_ssh_command(client,
            "cat /etc/systemd/system/ai-novel-agent.service",
            "当前服务配置")
        
        # 2.2 修复配置（使用正确的uvicorn命令）
        fixed_service = '''[Unit]
Description=ai-novel-agent (FastAPI)
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ai-novel-agent/backend
Environment="PATH=/opt/ai-novel-agent/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile=/opt/ai-novel-agent/backend/.env
ExecStart=/opt/ai-novel-agent/venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ai-novel-agent

[Install]
WantedBy=multi-user.target
'''
        
        # 写入修复后的配置
        run_ssh_command(client,
            f"cat > /etc/systemd/system/ai-novel-agent.service << 'EOF'\n{fixed_service}\nEOF",
            "写入修复的服务配置")
        
        # 2.3 重载systemd
        run_ssh_command(client,
            "systemctl daemon-reload",
            "重载systemd配置")
        
        # 步骤3: 检查环境配置
        print("\n3. 检查环境配置")
        
        # 3.1 检查.env文件位置
        run_ssh_command(client,
            "ls -la /opt/ai-novel-agent/backend/.env",
            "检查.env文件")
        
        # 3.2 确保.env文件存在且正确
        env_check_cmd = '''cat > /opt/ai-novel-agent/backend/.env << 'ENVEOF'
# DeepSeek API 配置
MOCK_LLM=0
LLM_PROVIDER=openai_compatible
LLM_API_BASE=https://api.deepseek.com
LLM_API_KEY=sk-7bfa809eeac74e168ee642d4e71b0958
LLM_MODEL=deepseek-chat

# 服务配置
AGENT_INTERVAL_SECONDS=2.0
STEP_INTERVAL_SECONDS=0.5
PORT=9000

# 数据目录
DATA_DIR=/opt/ai-novel-agent/backend/data
LOG_DIR=/opt/ai-novel-agent/backend/logs
ENVEOF'''
        
        run_ssh_command(client, env_check_cmd, "确保.env配置正确")
        
        # 步骤4: 启动服务
        print("\n4. 启动服务")
        
        # 4.1 停止服务（如果还在尝试重启）
        run_ssh_command(client,
            "systemctl stop ai-novel-agent.service",
            "停止服务")
        
        time.sleep(2)
        
        # 4.2 启动服务
        run_ssh_command(client,
            "systemctl start ai-novel-agent.service",
            "启动服务")
        
        # 4.3 等待启动
        time.sleep(3)
        
        # 4.4 检查状态
        _, status_output = run_ssh_command(client,
            "systemctl status ai-novel-agent.service --no-pager",
            "检查服务状态")
        
        # 步骤5: 验证修复
        print("\n5. 验证修复")
        
        # 5.1 检查进程
        run_ssh_command(client,
            "ps aux | grep 'uvicorn.*9000' | grep -v grep",
            "检查uvicorn进程")
        
        # 5.2 检查端口
        run_ssh_command(client,
            "ss -tlnp | grep :9000",
            "检查端口占用")
        
        # 5.3 测试API
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/health",
            "测试健康检查")
        
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/config",
            "测试配置API")
        
        # 5.4 检查日志
        run_ssh_command(client,
            "journalctl -u ai-novel-agent.service -n 10 --no-pager",
            "检查最近日志")
        
        client.close()
        
        print("\n" + "="*60)
        print("✅ 最终修复完成！")
        print("="*60)
        
        if "active (running)" in status_output:
            print("🎉 服务正常运行！")
        else:
            print("⚠️  服务可能仍有问题，请检查日志")
        
        print("\n📊 服务信息:")
        print("  地址: http://104.244.90.202:9000")
        print("  状态: systemctl status ai-novel-agent.service")
        print("  日志: journalctl -u ai-novel-agent.service -f")
        print("  配置: /opt/ai-novel-agent/backend/.env")
        
        print("\n🔧 下一步建议:")
        print("  1. 测试创建新任务是否成功")
        print("  2. 清理旧的失败任务数据")
        print("  3. 监控磁盘空间使用")
        print("  4. 检查DeepSeek API调用是否正常")
        
    except Exception as e:
        print(f"❌ 修复失败: {e}")

if __name__ == "__main__":
    final_fix()