#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"
LOCAL_CONF="stock_default.conf"

echo "🚀 强制接管 Nginx 默认站点..."

# 1. 上传新配置
echo "📤 上传配置文件..."
sshpass -p "$PASS" scp -o StrictHostKeyChecking=no $LOCAL_CONF $USER@$HOST:/tmp/stock.conf

# 2. 覆盖配置并重启
REMOTE_CMD="
echo '=== 1. 覆盖配置文件 ==='
mv /tmp/stock.conf /www/server/panel/vhost/nginx/stock.conf

echo '=== 2. 移除 phpfpm_status.conf (防止端口冲突) ==='
if [ -f /www/server/panel/vhost/nginx/phpfpm_status.conf ]; then
    mv /www/server/panel/vhost/nginx/phpfpm_status.conf /www/server/panel/vhost/nginx/phpfpm_status.conf.disabled
    echo '已禁用 phpfpm_status.conf'
fi

echo '=== 3. 重启 Nginx ==='
/www/server/nginx/sbin/nginx -t && /www/server/nginx/sbin/nginx -s reload
echo '✅ Nginx 重启成功'
"

sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$HOST "$REMOTE_CMD"

echo "------------------------------------------------"
echo "🎉 修复完成！请刷新浏览器访问 http://$HOST"
echo "------------------------------------------------"
