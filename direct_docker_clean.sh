#!/bin/bash
# 直接清理Docker脚本

echo "开始清理Docker..."

# 1. 停止Docker服务
echo "1. 停止Docker服务..."
systemctl stop docker
systemctl stop containerd

# 2. 杀死Docker进程
echo "2. 杀死Docker进程..."
pkill -f docker
pkill -f containerd
killall docker 2>/dev/null || true
killall containerd 2>/dev/null || true
killall dockerd 2>/dev/null || true

sleep 2

# 3. 强制杀死剩余进程
echo "3. 强制杀死剩余Docker进程..."
pkill -9 -f docker
pkill -9 -f containerd

# 4. 删除Docker数据目录
echo "4. 删除Docker数据目录..."
rm -rf /var/lib/docker
rm -rf /var/lib/containerd
rm -rf /etc/docker
rm -rf /var/run/docker.sock
rm -rf /var/run/containerd
rm -rf /opt/containerd

# 5. 禁用Docker服务
echo "5. 禁用Docker服务..."
systemctl disable docker
systemctl disable containerd
systemctl mask docker
systemctl mask containerd

# 6. 检查清理结果
echo "6. 检查清理结果..."
echo "Docker进程检查:"
ps aux | grep -E '(docker|containerd)' | grep -v grep || echo "无Docker进程"

echo ""
echo "Docker服务状态:"
systemctl status docker --no-pager 2>&1 | head -5

echo ""
echo "磁盘空间:"
df -h /

echo ""
echo "ai-novel-agent服务状态:"
systemctl status ai-novel-agent --no-pager | head -5

echo ""
echo "Docker清理完成！"