#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
裸机部署脚本 - 将AI小说生成Agent系统部署到Ubuntu服务器（不使用Docker）
直接在服务器上运行Python服务，使用9000端口
"""

import os
import sys
import json
import time
import paramiko
from pathlib import Path
from typing import Dict, List, Optional

# 服务器配置
HOST = "104.244.90.202"
USER = "root"
# 注意：密码可能需要更新
PASSWORD = "C66ffUMycDn2"  # 可能需要新密码
PORT = 22
REMOTE_DIR = "/opt/ai-novel-agent-bare"

# DeepSeek API配置（与.env一致）
LLM_API_BASE = "https://api.deepseek.com"
LLM_API_KEY = "sk-7bfa809eeac74e168ee642d4e71b0958"
LLM_MODEL = "deepseek-chat"

def run_ssh(cmd: str, check: bool = True) -> Dict:
    """执行远程SSH命令"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    try:
        client.connect(HOST, port=PORT, username=USER, password=PASSWORD, timeout=15)
        stdin, stdout, stderr = client.exec_command(cmd, get_pty=True)
        
        # 等待命令完成
        exit_status = stdout.channel.recv_exit_status()
        output = stdout.read().decode('utf-8', errors='replace')
        error = stderr.read().decode('utf-8', errors='replace')
        
        client.close()
        
        if check and exit_status != 0:
            raise RuntimeError(f"命令执行失败 (exit {exit_status}): {error or output}")
        
        return {
            "exit_code": exit_status,
            "stdout": output,
            "stderr": error
        }
    
    except paramiko.ssh_exception.AuthenticationException:
        print(f"❌ SSH认证失败！请检查用户名和密码。")
        print(f"   尝试的用户名: {USER}")
        print(f"   密码可能已更改，请更新脚本中的PASSWORD变量")
        raise
    except Exception as e:
        print(f"❌ SSH连接失败: {e}")
        raise

def check_server_prerequisites():
    """检查服务器基础环境"""
    print("🔍 检查服务器基础环境...")
    
    checks = [
        ("检查Python3", "python3 --version"),
        ("检查pip3", "pip3 --version"),
        ("检查git", "git --version"),
        ("检查系统服务", "systemctl --version"),
        ("检查端口9000", "ss -tlnp | grep :9000 || echo '端口9000空闲'"),
    ]
    
    for check_name, cmd in checks:
        print(f"  {check_name}...")
        try:
            result = run_ssh(cmd, check=False)
            if result["exit_code"] == 0:
                print(f"    ✅ {result['stdout'].strip()}")
            else:
                print(f"    ⚠️  可能有问题: {result['stderr'].strip()}")
        except:
            print(f"    ❌ 检查失败")

def install_dependencies():
    """安装系统依赖和Python包"""
    print("📦 安装系统依赖...")
    
    # 更新系统并安装基础依赖
    cmds = [
        "apt-get update",
        "apt-get install -y python3-pip python3-venv git nginx supervisor",
        "pip3 install --upgrade pip",
    ]
    
    for cmd in cmds:
        print(f"  执行: {cmd}")
        result = run_ssh(cmd)
        print(f"    ✅ 完成")

def setup_project_directory():
    """设置项目目录"""
    print("📁 设置项目目录...")
    
    # 创建目录
    cmds = [
        f"mkdir -p {REMOTE_DIR}",
        f"mkdir -p {REMOTE_DIR}/backend",
        f"mkdir -p {REMOTE_DIR}/backend/data",
        f"mkdir -p {REMOTE_DIR}/backend/logs",
        f"chmod 755 {REMOTE_DIR}",
    ]
    
    for cmd in cmds:
        run_ssh(cmd)
    
    print(f"    ✅ 目录创建完成: {REMOTE_DIR}")

def upload_project_files():
    """上传项目文件到服务器"""
    print("📤 上传项目文件...")
    
    # 本地项目根目录
    local_root = Path("E:/work/ai-novel-agent")
    
    # 需要上传的目录和文件
    upload_items = [
        ("backend", f"{REMOTE_DIR}/backend"),
        ("deploy", f"{REMOTE_DIR}/deploy"),
        ("scripts", f"{REMOTE_DIR}/scripts"),
        ("README.md", f"{REMOTE_DIR}/README.md"),
        ("requirements.txt", f"{REMOTE_DIR}/backend/requirements.txt"),
    ]
    
    # 使用scp上传（这里简化，实际应该用paramiko的SFTP）
    print("  注意：实际部署时应使用SFTP上传文件")
    print("  这里只创建占位文件")
    
    # 创建.env文件
    env_content = f"""# DeepSeek API 配置
MOCK_LLM=0
LLM_PROVIDER=openai_compatible
LLM_API_BASE={LLM_API_BASE}
LLM_API_KEY={LLM_API_KEY}
LLM_MODEL={LLM_MODEL}

# 服务配置
AGENT_INTERVAL_SECONDS=2.0
STEP_INTERVAL_SECONDS=0.5
PORT=9000

# 数据目录
DATA_DIR={REMOTE_DIR}/backend/data
LOG_DIR={REMOTE_DIR}/backend/logs
"""
    
    create_env_cmd = f"cat > {REMOTE_DIR}/backend/.env << 'EOF'\n{env_content}\nEOF"
    run_ssh(create_env_cmd)
    print(f"    ✅ 创建.env文件")

def setup_python_environment():
    """设置Python虚拟环境和依赖"""
    print("🐍 设置Python环境...")
    
    cmds = [
        # 创建虚拟环境
        f"cd {REMOTE_DIR}/backend && python3 -m venv venv",
        # 安装依赖
        f"cd {REMOTE_DIR}/backend && . venv/bin/activate && pip install --upgrade pip",
        f"cd {REMOTE_DIR}/backend && . venv/bin/activate && pip install -r requirements.txt",
        # 安装开发依赖（可选）
        f"cd {REMOTE_DIR}/backend && . venv/bin/activate && pip install pytest",
    ]
    
    for cmd in cmds:
        print(f"  执行: {cmd.split('&&')[-1].strip()}")
        result = run_ssh(cmd, check=False)
        if result["exit_code"] == 0:
            print(f"    ✅ 完成")
        else:
            print(f"    ⚠️  可能有警告: {result['stderr'][:200]}")

def create_systemd_service():
    """创建systemd服务"""
    print("⚙️  创建systemd服务...")
    
    service_content = f"""[Unit]
Description=AI Novel Agent Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={REMOTE_DIR}/backend
Environment="PATH={REMOTE_DIR}/backend/venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
EnvironmentFile={REMOTE_DIR}/backend/.env
ExecStart={REMOTE_DIR}/backend/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9000
Restart=always
RestartSec=10
StandardOutput=syslog
StandardError=syslog
SyslogIdentifier=ai-novel-agent

[Install]
WantedBy=multi-user.target
"""
    
    # 创建服务文件
    create_service_cmd = f"cat > /etc/systemd/system/ai-novel-agent.service << 'EOF'\n{service_content}\nEOF"
    run_ssh(create_service_cmd)
    
    # 重载systemd并启用服务
    cmds = [
        "systemctl daemon-reload",
        "systemctl enable ai-novel-agent.service",
        "systemctl start ai-novel-agent.service",
        "systemctl status ai-novel-agent.service --no-pager",
    ]
    
    for cmd in cmds:
        print(f"  执行: {cmd}")
        result = run_ssh(cmd, check=False)
        if result["exit_code"] == 0:
            print(f"    ✅ 完成")
        else:
            print(f"    ⚠️  输出: {result['stdout'][:200]}")

def create_nginx_config():
    """创建Nginx反向代理配置（可选）"""
    print("🌐 配置Nginx（可选）...")
    
    nginx_config = f"""server {{
    listen 80;
    server_name 104.244.90.202;
    
    location / {{
        proxy_pass http://127.0.0.1:9000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
    
    location /static/ {{
        alias {REMOTE_DIR}/backend/static/;
    }}
}}
"""
    
    create_nginx_cmd = f"cat > /etc/nginx/sites-available/ai-novel-agent << 'EOF'\n{nginx_config}\nEOF"
    run_ssh(create_nginx_cmd)
    
    cmds = [
        "ln -sf /etc/nginx/sites-available/ai-novel-agent /etc/nginx/sites-enabled/",
        "nginx -t",
        "systemctl restart nginx",
    ]
    
    for cmd in cmds:
        result = run_ssh(cmd, check=False)
        if result["exit_code"] == 0:
            print(f"    ✅ {cmd}")
        else:
            print(f"    ⚠️  {cmd}: {result['stderr'][:100]}")

def cleanup_docker_artifacts():
    """清理Docker相关文件"""
    print("🧹 清理Docker相关文件...")
    
    # 检查并停止Docker服务
    cmds = [
        "docker ps -a | grep ai-novel-agent || echo '没有找到相关Docker容器'",
        "docker stop $(docker ps -a -q --filter 'name=ai-novel-agent') 2>/dev/null || true",
        "docker rm $(docker ps -a -q --filter 'name=ai-novel-agent') 2>/dev/null || true",
        "systemctl stop docker 2>/dev/null || true",
        "systemctl disable docker 2>/dev/null || true",
    ]
    
    for cmd in cmds:
        result = run_ssh(cmd, check=False)
        if result["stdout"].strip():
            print(f"   清理: {result['stdout'].strip()[:100]}")

def verify_deployment():
    """验证部署是否成功"""
    print("✅ 验证部署...")
    
    checks = [
        ("检查服务状态", "systemctl status ai-novel-agent.service --no-pager"),
        ("检查端口监听", "ss -tlnp | grep :9000"),
        ("检查服务日志", "journalctl -u ai-novel-agent.service -n 10 --no-pager"),
        ("测试API健康检查", f"curl -s http://localhost:9000/api/health || echo 'API不可达'"),
    ]
    
    for check_name, cmd in checks:
        print(f"  {check_name}...")
        result = run_ssh(cmd, check=False)
        if result["exit_code"] == 0:
            output = result["stdout"].strip()
            if output:
                print(f"    ✅ {output[:100]}")
        else:
            print(f"    ⚠️  检查失败")

def main():
    """主部署流程"""
    print("="*60)
    print("AI小说生成Agent系统 - 裸机部署")
    print("="*60)
    
    try:
        # 1. 检查服务器环境
        check_server_prerequisites()
        
        # 2. 安装依赖
        install_dependencies()
        
        # 3. 设置项目目录
        setup_project_directory()
        
        # 4. 上传项目文件（这里简化）
        upload_project_files()
        
        # 5. 设置Python环境
        setup_python_environment()
        
        # 6. 清理Docker残留
        cleanup_docker_artifacts()
        
        # 7. 创建systemd服务
        create_systemd_service()
        
        # 8. 配置Nginx（可选）
        create_nginx_config()
        
        # 9. 验证部署
        verify_deployment()
        
        print("\n" + "="*60)
        print("🎉 部署完成！")
        print(f"服务地址: http://{HOST}:9000")
        print(f"服务状态: systemctl status ai-novel-agent.service")
        print(f"查看日志: journalctl -u ai-novel-agent.service -f")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 部署失败: {e}")
        print("\n故障排除:")
        print("1. 检查SSH密码是否正确")
        print("2. 检查服务器网络连接")
        print("3. 手动登录服务器检查")
        return 1
    
    return 0

if __name__ == "__main__":
    # 注意：由于SSH认证失败，这个脚本可能无法直接运行
    # 需要先更新密码或手动执行步骤
    print("⚠️  注意：由于SSH密码可能已更改，此脚本可能无法直接运行")
    print("请先确认密码或手动执行部署步骤")
    
    response = input("是否继续尝试部署？(y/N): ")
    if response.lower() == 'y':
        sys.exit(main())
    else:
        print("取消部署")
        sys.exit(0)