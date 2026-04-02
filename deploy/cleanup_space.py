#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
清理服务器磁盘空间
"""

import paramiko
import sys

def cleanup_server():
    """清理服务器磁盘空间"""
    
    server_config = {
        "host": "104.244.90.202",
        "port": 22,
        "username": "root",
        "password": "v9wSxMxg92dp"
    }
    
    print("清理服务器磁盘空间...")
    
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
        
        def run_command(cmd, description=""):
            """运行命令并打印输出"""
            if description:
                print(f"\n{description}")
            print(f"执行: {cmd}")
            
            stdin, stdout, stderr = client.exec_command(cmd)
            output = stdout.read().decode('utf-8', errors='ignore')
            error = stderr.read().decode('utf-8', errors='ignore')
            
            if output:
                print(f"输出: {output}")
            if error:
                print(f"错误: {error}")
            
            return output, error
        
        # 1. 检查磁盘空间
        print("\n1. 当前磁盘空间:")
        run_command("df -h")
        
        # 2. 清理Docker相关文件（如果存在）
        print("\n2. 清理Docker相关文件:")
        run_command("docker system prune -f 2>/dev/null || echo 'Docker未安装'")
        run_command("docker volume prune -f 2>/dev/null || echo '无Docker卷'")
        
        # 3. 清理日志文件
        print("\n3. 清理日志文件:")
        run_command("journalctl --vacuum-time=1d", "清理1天前的系统日志")
        run_command("find /var/log -name '*.log' -type f -mtime +7 -delete 2>/dev/null || true", "删除7天前的日志")
        run_command("find /tmp -type f -mtime +1 -delete 2>/dev/null || true", "清理/tmp目录")
        
        # 4. 清理备份文件
        print("\n4. 清理旧备份:")
        run_command("find /opt -name '*backup*' -type d -mtime +3 -exec rm -rf {} \; 2>/dev/null || true", "删除3天前的备份")
        run_command("find /opt -name '*.backup' -type f -mtime +3 -delete 2>/dev/null || true", "删除备份文件")
        
        # 5. 清理Python缓存
        print("\n5. 清理Python缓存:")
        run_command("find /opt/ai-novel-agent -name '__pycache__' -type d -exec rm -rf {} \; 2>/dev/null || true")
        run_command("find /opt/ai-novel-agent -name '*.pyc' -delete 2>/dev/null || true")
        
        # 6. 清理venv目录（如果需要）
        print("\n6. 检查venv目录:")
        run_command("du -sh /opt/ai-novel-agent/backend/venv 2>/dev/null || echo 'venv目录不存在'")
        
        # 7. 删除大文件
        print("\n7. 查找大文件:")
        run_command("find /opt -type f -size +100M -exec ls -lh {} \; 2>/dev/null | head -10", "查找大于100M的文件")
        
        # 8. 再次检查磁盘空间
        print("\n8. 清理后的磁盘空间:")
        run_command("df -h")
        
        print("\n清理完成!")
        client.close()
        return True
        
    except Exception as e:
        print(f"清理失败: {e}")
        return False

def main():
    print("服务器磁盘空间清理工具")
    print("=" * 60)
    
    success = cleanup_server()
    
    if success:
        print("\n[OK] 清理成功!")
    else:
        print("\n[FAIL] 清理失败!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)