#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程执行部署脚本
"""

import paramiko
import sys

def execute_remote_script():
    """在远程服务器上执行部署脚本"""
    
    server_config = {
        "host": "104.244.90.202",
        "port": 22,
        "username": "root",
        "password": "v9wSxMxg92dp"
    }
    
    print("连接到服务器执行部署脚本...")
    
    try:
        # 连接到服务器
        client = paramiko.SSHClient()
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(
            hostname=server_config['host'],
            port=server_config['port'],
            username=server_config['username'],
            password=server_config['password'],
            timeout=30
        )
        
        # 读取本地脚本内容
        with open('deploy/direct_update.sh', 'r', encoding='utf-8') as f:
            script_content = f.read()
        
        # 上传脚本到服务器
        print("上传部署脚本到服务器...")
        sftp = client.open_sftp()
        
        # 创建临时脚本文件
        remote_script = "/tmp/update_ai_novel_agent.sh"
        with sftp.file(remote_script, 'w') as f:
            f.write(script_content)
        
        # 设置执行权限
        client.exec_command(f"chmod +x {remote_script}")
        
        # 执行脚本
        print("执行部署脚本...")
        stdin, stdout, stderr = client.exec_command(f"bash {remote_script}")
        
        # 实时输出
        print("部署输出:")
        for line in stdout:
            print(line.strip())
        
        # 检查错误
        error = stderr.read().decode('utf-8', errors='ignore')
        if error:
            print("错误输出:")
            print(error)
        
        # 检查退出状态
        exit_status = stdout.channel.recv_exit_status()
        
        if exit_status == 0:
            print("\n部署成功!")
            
            # 验证服务
            print("\n验证服务状态...")
            stdin, stdout, stderr = client.exec_command("curl -s http://localhost:9000/api/health")
            output = stdout.read().decode('utf-8', errors='ignore')
            print(f"健康检查: {output}")
            
        else:
            print(f"\n部署失败，退出状态: {exit_status}")
        
        # 清理临时文件
        client.exec_command(f"rm -f {remote_script}")
        
        # 关闭连接
        sftp.close()
        client.close()
        
        return exit_status == 0
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """主函数"""
    print("AI Novel Media Agent 远程部署")
    print("=" * 60)
    
    success = execute_remote_script()
    
    if success:
        print("\n" + "=" * 60)
        print("部署完成!")
        print("访问地址: http://104.244.90.202:9000/")
        print("API文档: http://104.244.90.202:9000/api/health")
    else:
        print("\n部署失败!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)