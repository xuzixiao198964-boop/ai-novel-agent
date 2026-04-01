#!/bin/bash
# 快速完全清除Docker

echo "=== 快速完全清除Docker ==="

echo "1. 停止Docker服务..."
systemctl stop docker containerd docker.socket 2>/dev/null
pkill -9 -f docker
pkill -9 -f containerd

echo "2. 卸载Docker包..."
apt-get remove --purge -y docker.io docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin 2>/dev/null
apt-get remove --purge -y docker docker-engine docker.io containerd runc 2>/dev/null
apt-get autoremove -y
apt-get autoclean -y
apt-get purge -y docker-* containerd-* 2>/dev/null

echo "3. 删除Docker目录..."
rm -rf /var/lib/docker
rm -rf /var/lib/containerd
rm -rf /etc/docker
rm -rf /etc/containerd
rm -rf /var/run/docker.sock
rm -rf /var/run/docker
rm -rf /var/run/containerd
rm -rf /opt/containerd
rm -rf /opt/docker
rm -rf /var/log/docker
rm -rf /var/log/containerd

echo "4. 删除Docker二进制文件..."
rm -f /usr/bin/docker
rm -f /usr/bin/dockerd
rm -f /usr/bin/containerd
rm -f /usr/bin/docker-compose
rm -f /usr/local/bin/docker
rm -f /usr/local/bin/docker-compose

echo "5. 清理用户配置..."
rm -rf ~/.docker
rm -rf ~/.config/docker
rm -rf /root/.docker
rm -rf /root/.config/docker

echo "6. 清理系统配置..."
rm -rf /etc/systemd/system/docker.service.d
rm -rf /etc/systemd/system/containerd.service.d
rm -f /etc/systemd/system/docker.service
rm -f /etc/systemd/system/containerd.service
rm -f /etc/systemd/system/docker.socket
systemctl daemon-reload

echo "7. 验证清理结果..."
echo "Docker命令检查:"
which docker 2>/dev/null || echo "Docker命令不存在"

echo ""
echo "Docker进程检查:"
ps aux | grep -E '(docker|containerd)' | grep -v grep || echo "无Docker进程"

echo ""
echo "Docker包检查:"
dpkg -l | grep -E '(docker|containerd)' 2>/dev/null || echo "无Docker相关包"

echo ""
echo "主要文件检查:"
for file in /usr/bin/docker /usr/bin/dockerd /usr/bin/containerd /var/lib/docker /var/lib/containerd /etc/docker; do
    if [ -e "$file" ]; then
        echo "警告: $file 仍存在"
    else
        echo "OK: $file 已删除"
    fi
done

echo ""
echo "ai-novel-agent服务状态:"
systemctl status ai-novel-agent --no-pager | head -5

echo ""
echo "磁盘空间:"
df -h /

echo ""
echo "=== Docker完全清除完成 ==="