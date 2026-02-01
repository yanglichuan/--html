#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"

REMOTE_CMD="
echo '=== 1. 检查 Nginx 状态 ==='
/www/server/nginx/sbin/nginx -t

echo -e '\n=== 2. 列出所有站点配置 ==='
ls -l /www/server/panel/vhost/nginx/

echo -e '\n=== 3. 检查是否有默认站点冲突 ==='
grep -r 'default_server' /www/server/panel/vhost/nginx/
grep -r 'listen 80' /www/server/panel/vhost/nginx/
grep -r 'server_name' /www/server/panel/vhost/nginx/

echo -e '\n=== 4. 尝试重命名可能冲突的默认配置 ==='
if [ -f /www/server/panel/vhost/nginx/0.default.conf ]; then
    mv /www/server/panel/vhost/nginx/0.default.conf /www/server/panel/vhost/nginx/0.default.conf.bak
    echo '已禁用 0.default.conf'
fi

echo -e '\n=== 5. 确保 stock.conf 存在且正确 ==='
cat /www/server/panel/vhost/nginx/stock.conf

echo -e '\n=== 6. 重启 Nginx ==='
/www/server/nginx/sbin/nginx -s reload
echo 'Nginx 已重启'
"

sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$HOST "$REMOTE_CMD"
