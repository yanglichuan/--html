#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"

REMOTE_CMD="
echo '=== 1. 深度检查 IPTABLES ==='
iptables-save

echo -e '\n=== 2. 检查路由表 ==='
ip route show

echo -e '\n=== 3. 检查 SELinux ==='
sestatus || echo 'SELinux not installed'

echo -e '\n=== 4. 测试本地访问 (curl localhost) ==='
curl -I localhost

echo -e '\n=== 5. 测试本地访问 (curl 公网IP) ==='
curl -I 101.42.116.50
"

sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$HOST "$REMOTE_CMD"
