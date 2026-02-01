#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"

REMOTE_CMD="
echo '=== 1. 检查防火墙状态 ==='
if command -v firewall-cmd >/dev/null; then
    echo '>> Firewalld 状态:'
    firewall-cmd --state
    echo '>> 开放端口:'
    firewall-cmd --list-ports
elif command -v ufw >/dev/null; then
    echo '>> UFW 状态:'
    ufw status
fi

echo -e '\n=== 2. 检查 iptables ==='
iptables -L INPUT -n --line-numbers | grep 80

echo -e '\n=== 3. 检查端口监听 ==='
netstat -tulpn | grep :80

echo -e '\n=== 4. 尝试放行 80 端口 (Firewalld) ==='
if command -v firewall-cmd >/dev/null; then
    firewall-cmd --zone=public --add-port=80/tcp --permanent
    firewall-cmd --reload
    echo '✅ 已尝试通过 Firewalld 放行 80 端口'
fi
"

sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$HOST "$REMOTE_CMD"
