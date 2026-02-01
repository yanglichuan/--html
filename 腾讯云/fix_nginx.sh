#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"
LOCAL_CONF="stock.conf"
REMOTE_CONF_DIR="/www/server/panel/vhost/nginx"

echo "🚀 上传 Nginx 配置文件..."

# 1. 上传配置文件的 expect 脚本
cat > upload_conf.exp <<EOF
#!/usr/bin/expect
set timeout 20
spawn scp -o StrictHostKeyChecking=no $LOCAL_CONF $USER@$HOST:/tmp/stock.conf
expect {
    "password:" { send "$PASS\r"; exp_continue }
    eof
}
EOF

chmod +x upload_conf.exp
./upload_conf.exp
rm upload_conf.exp

# 2. 移动配置并重启 Nginx 的 expect 脚本
cat > restart_nginx.exp <<EOF
#!/usr/bin/expect
set timeout 20
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST
expect {
    "password:" { send "$PASS\r"; exp_continue }
    "#" {
        send "mv /tmp/stock.conf $REMOTE_CONF_DIR/stock.conf\r"
        send "echo '🔍 检查 Nginx 配置...'\r"
        send "/www/server/nginx/sbin/nginx -t\r"
        send "echo '🔄 重载 Nginx...'\r"
        send "/www/server/nginx/sbin/nginx -s reload\r"
        send "exit\r"
    }
}
expect eof
EOF

echo "🔄 正在应用配置并重启 Nginx..."
chmod +x restart_nginx.exp
./restart_nginx.exp
rm restart_nginx.exp

echo "------------------------------------------------"
echo "✅ 配置已更新！"
echo "请再次尝试访问: http://$HOST"
echo "------------------------------------------------"
