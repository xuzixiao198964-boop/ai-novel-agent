import paramiko
import sys
import time

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def install_missing_deps():
    # 服务器信息
    HOST = "104.244.90.202"
    USER = "root"
    PASSWORD = "v9wSxMxg92dp"
    PORT = 22
    
    print("=== 安装缺失的依赖包 ===")
    
    try:
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=10)
        
        print("✅ 已连接到服务器")
        
        # 1. 检查当前虚拟环境和依赖
        print("\n1. 检查当前环境:")
        run_ssh_command(client,
            "ls -la /opt/ai-novel-agent/venv/bin/python",
            "检查虚拟环境")
        
        run_ssh_command(client,
            "cat /opt/ai-novel-agent/backend/requirements.txt | head -20",
            "查看requirements.txt")
        
        # 2. 安装缺失的依赖
        print("\n2. 安装缺失依赖:")
        
        # 2.1 激活虚拟环境并安装httpx
        install_cmd = '''cd /opt/ai-novel-agent/backend && \
source ../venv/bin/activate && \
pip install httpx
'''
        
        run_ssh_command(client, install_cmd, "安装httpx")
        
        # 2.2 安装其他可能缺失的依赖
        install_all_cmd = '''cd /opt/ai-novel-agent/backend && \
source ../venv/bin/activate && \
pip install -r requirements.txt
'''
        
        run_ssh_command(client, install_all_cmd, "安装所有依赖")
        
        # 3. 验证依赖安装
        print("\n3. 验证依赖安装:")
        
        verify_cmd = '''cd /opt/ai-novel-agent/backend && \
source ../venv/bin/activate && \
python -c "import httpx; import fastapi; import uvicorn; import pydantic; print('✅ 所有关键依赖已安装')"
'''
        
        run_ssh_command(client, verify_cmd, "验证依赖")
        
        # 4. 测试配置导入
        print("\n4. 测试配置导入:")
        
        test_config_cmd = '''cd /opt/ai-novel-agent/backend && \
source ../venv/bin/activate && \
python -c "
import sys
sys.path.insert(0, '.')

try:
    from app.core.config import settings
    print('✅ 配置导入成功！')
    # 列出所有配置字段
    print('配置字段:')
    for attr in dir(settings):
        if not attr.startswith('_'):
            try:
                value = getattr(settings, attr)
                if callable(value):
                    continue
                if 'key' in attr.lower() and value:
                    print(f'  {attr}: ********')
                else:
                    print(f'  {attr}: {value}')
            except:
                pass
except Exception as e:
    print(f'❌ 配置导入失败: {e}')
    import traceback
    traceback.print_exc()
"
'''
        
        run_ssh_command(client, test_config_cmd, "测试配置")
        
        # 5. 重启服务
        print("\n5. 重启服务:")
        
        # 5.1 停止服务
        run_ssh_command(client,
            "systemctl stop ai-novel-agent.service",
            "停止服务")
        
        time.sleep(2)
        
        # 5.2 确保端口释放
        run_ssh_command(client,
            "ss -tlnp | grep :9000 || echo '端口已释放'",
            "检查端口")
        
        # 5.3 启动服务
        run_ssh_command(client,
            "systemctl start ai-novel-agent.service",
            "启动服务")
        
        # 5.4 等待启动
        time.sleep(5)
        
        # 6. 检查服务状态
        print("\n6. 检查服务状态:")
        
        run_ssh_command(client,
            "systemctl status ai-novel-agent.service --no-pager | head -15",
            "服务状态")
        
        run_ssh_command(client,
            "ps aux | grep 'uvicorn.*9000' | grep -v grep",
            "进程状态")
        
        run_ssh_command(client,
            "ss -tlnp | grep :9000",
            "端口占用")
        
        # 7. 测试API
        print("\n7. 测试API:")
        
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/health",
            "健康检查")
        
        run_ssh_command(client,
            "curl -s http://localhost:9000/api/config",
            "配置API")
        
        # 8. 查看日志
        print("\n8. 查看日志:")
        
        run_ssh_command(client,
            "journalctl -u ai-novel-agent.service -n 20 --no-pager",
            "最近日志")
        
        client.close()
        
        print("\n" + "="*60)
        print("✅ 依赖安装完成")
        
    except Exception as e:
        print(f"❌ 安装失败: {e}")

def run_ssh_command(client, cmd, description):
    """执行SSH命令"""
    print(f"\n{description}:")
    print(f"  执行: {cmd}")
    
    try:
        stdin, stdout, stderr = client.exec_command(cmd, timeout=15)
        output = stdout.read().decode('utf-8', errors='replace').strip()
        error = stderr.read().decode('utf-8', errors='replace').strip()
        
        if output:
            print(f"  {output[:300]}")
        if error and "WARNING" not in error:
            print(f"  ⚠️  错误: {error[:200]}")
    except Exception as e:
        print(f"  ❌ 执行异常: {e}")

if __name__ == "__main__":
    install_missing_deps()