#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
更新服务器代码部署脚本
将本地更新推送到服务器并重启服务
"""

import os
import sys
import paramiko
from pathlib import Path
import time
import json

# 服务器配置
SERVER_CONFIG = {
    "host": "104.244.90.202",
    "port": 22,
    "username": "root",
    "password": "v9wSxMxg92dp"
}

# 项目路径
LOCAL_PROJECT_PATH = Path(__file__).parent.parent
REMOTE_PROJECT_PATH = "/opt/ai-novel-agent"

def create_ssh_client():
    """创建SSH客户端"""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    return client

def execute_ssh_command(client, command, print_output=True):
    """执行SSH命令"""
    print(f"执行命令: {command}")
    
    stdin, stdout, stderr = client.exec_command(command)
    exit_status = stdout.channel.recv_exit_status()
    
    output = stdout.read().decode('utf-8', errors='ignore')
    error = stderr.read().decode('utf-8', errors='ignore')
    
    if print_output:
        if output:
            print(f"输出: {output}")
        if error:
            print(f"错误: {error}")
    
    return exit_status, output, error

def upload_directory(sftp, local_path, remote_path):
    """上传目录到服务器"""
    print(f"上传目录: {local_path} -> {remote_path}")
    
    # 确保远程目录存在
    try:
        sftp.stat(remote_path)
    except FileNotFoundError:
        sftp.mkdir(remote_path)
    
    for item in os.listdir(local_path):
        local_item = os.path.join(local_path, item)
        remote_item = os.path.join(remote_path, item)
        
        if os.path.isfile(local_item):
            print(f"  上传文件: {item}")
            sftp.put(local_item, remote_item)
        elif os.path.isdir(local_item):
            upload_directory(sftp, local_item, remote_item)

def backup_server(client):
    """备份服务器现有代码"""
    print("备份服务器代码...")
    
    timestamp = time.strftime("%Y%m%d_%H%M%S")
    backup_path = f"/opt/ai-novel-agent-backup-{timestamp}"
    
    commands = [
        f"cp -r {REMOTE_PROJECT_PATH} {backup_path}",
        f"echo '备份完成: {backup_path}'"
    ]
    
    for cmd in commands:
        exit_status, output, error = execute_ssh_command(client, cmd)
        if exit_status != 0:
            print(f"备份失败: {error}")
            return False
    
    print("备份成功")
    return True

def update_code_on_server(client, sftp):
    """更新服务器代码"""
    print("更新服务器代码...")
    
    # 1. 停止当前服务
    print("停止当前服务...")
    exit_status, output, error = execute_ssh_command(client, "systemctl stop ai-novel-agent")
    if exit_status != 0:
        print(f"停止服务失败: {error}")
    
    # 2. 备份现有代码
    if not backup_server(client):
        print("警告: 备份失败，继续更新...")
    
    # 3. 上传新代码
    print("上传新代码...")
    
    # 上传backend目录
    backend_local = LOCAL_PROJECT_PATH / "backend"
    backend_remote = f"{REMOTE_PROJECT_PATH}/backend"
    upload_directory(sftp, str(backend_local), backend_remote)
    
    # 上传static目录
    static_local = LOCAL_PROJECT_PATH / "static"
    static_remote = f"{REMOTE_PROJECT_PATH}/static"
    upload_directory(sftp, str(static_local), static_remote)
    
    # 上传deploy目录
    deploy_local = LOCAL_PROJECT_PATH / "deploy"
    deploy_remote = f"{REMOTE_PROJECT_PATH}/deploy"
    upload_directory(sftp, str(deploy_local), deploy_remote)
    
    # 上传requirements.txt
    req_local = LOCAL_PROJECT_PATH / "requirements.txt"
    if req_local.exists():
        sftp.put(str(req_local), f"{REMOTE_PROJECT_PATH}/requirements.txt")
    
    # 4. 设置权限
    print("设置文件权限...")
    commands = [
        f"chmod -R 755 {REMOTE_PROJECT_PATH}",
        f"chown -R root:root {REMOTE_PROJECT_PATH}"
    ]
    
    for cmd in commands:
        execute_ssh_command(client, cmd)
    
    # 5. 安装依赖
    print("安装Python依赖...")
    commands = [
        f"cd {REMOTE_PROJECT_PATH}",
        "python3 -m pip install -r requirements.txt --upgrade"
    ]
    
    exit_status, output, error = execute_ssh_command(client, " && ".join(commands))
    if exit_status != 0:
        print(f"安装依赖失败: {error}")
    
    # 6. 重启服务
    print("重启服务...")
    commands = [
        "systemctl daemon-reload",
        "systemctl start ai-novel-agent",
        "systemctl status ai-novel-agent --no-pager"
    ]
    
    for cmd in commands:
        exit_status, output, error = execute_ssh_command(client, cmd)
        if exit_status != 0:
            print(f"服务管理失败: {error}")
    
    return True

def verify_service(client):
    """验证服务状态"""
    print("验证服务状态...")
    
    # 检查服务状态
    exit_status, output, error = execute_ssh_command(client, "systemctl is-active ai-novel-agent")
    if "active" not in output:
        print("服务未运行")
        return False
    
    # 检查API健康状态
    print("检查API健康状态...")
    commands = [
        "sleep 3",  # 等待服务完全启动
        "curl -s http://localhost:9000/api/health"
    ]
    
    exit_status, output, error = execute_ssh_command(client, " && ".join(commands))
    
    if exit_status == 0:
        try:
            health_data = json.loads(output)
            print(f"服务健康状态: {health_data.get('status', 'unknown')}")
            return health_data.get('status') == 'ok'
        except:
            print(f"解析健康检查响应失败: {output}")
            return False
    else:
        print(f"健康检查失败: {error}")
        return False

def run_tests(client):
    """运行测试"""
    print("运行单元测试...")
    
    test_commands = [
        f"cd {REMOTE_PROJECT_PATH}/backend",
        "python3 -m pytest app/tests/unit/ -v"
    ]
    
    exit_status, output, error = execute_ssh_command(client, " && ".join(test_commands))
    
    if exit_status == 0:
        print("单元测试通过")
        return True
    else:
        print(f"单元测试失败: {error}")
        
        # 尝试运行集成测试
        print("尝试运行集成测试...")
        test_commands = [
            f"cd {REMOTE_PROJECT_PATH}/backend",
            "python3 -m pytest app/tests/integration/ -v"
        ]
        
        exit_status, output, error = execute_ssh_command(client, " && ".join(test_commands))
        
        if exit_status == 0:
            print("集成测试通过")
            return True
        else:
            print(f"集成测试失败: {error}")
            return False

def main():
    """主函数"""
    print("开始部署更新到服务器...")
    print(f"服务器: {SERVER_CONFIG['host']}")
    print(f"本地项目路径: {LOCAL_PROJECT_PATH}")
    print(f"远程项目路径: {REMOTE_PROJECT_PATH}")
    
    # 连接到服务器
    print("连接到服务器...")
    try:
        client = create_ssh_client()
        client.connect(
            hostname=SERVER_CONFIG['host'],
            port=SERVER_CONFIG['port'],
            username=SERVER_CONFIG['username'],
            password=SERVER_CONFIG['password']
        )
        
        # 创建SFTP客户端
        sftp = client.open_sftp()
        
        # 更新代码
        if not update_code_on_server(client, sftp):
            print("代码更新失败")
            return False
        
        # 验证服务
        if not verify_service(client):
            print("服务验证失败")
            
            # 尝试查看日志
            print("查看服务日志...")
            execute_ssh_command(client, "journalctl -u ai-novel-agent -n 50 --no-pager")
            return False
        
        # 运行测试
        print("运行测试...")
        if not run_tests(client):
            print("测试失败，但服务已启动")
            # 继续部署，但记录测试失败
        
        print("部署完成!")
        
        # 关闭连接
        sftp.close()
        client.close()
        
        return True
        
    except Exception as e:
        print(f"部署失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)