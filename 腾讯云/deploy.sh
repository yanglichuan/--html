#!/bin/bash

# 服务器信息
HOST="101.42.116.50"
USER="root"
PASS="123456aA"
LOCAL_FILE="index.html"
# 尝试多个可能的 Web 根目录
REMOTE_PATHS=("/www/server/nginx/html" "/usr/share/nginx/html" "/www/wwwroot/default")

echo "🚀 开始部署到腾讯云 ($HOST)..."

# 创建 expect 脚本用于 SCP
cat > upload.exp <<EOF
#!/usr/bin/expect
set timeout 20
spawn scp -o StrictHostKeyChecking=no $LOCAL_FILE $USER@$HOST:/tmp/uploaded_index.html
expect {
    "password:" { send "$PASS\r"; exp_continue }
    eof
}
EOF

# 执行上传
echo "📤 正在上传文件..."
chmod +x upload.exp
./upload.exp
rm upload.exp

# 创建 expect 脚本用于 SSH 移动文件
cat > move.exp <<EOF
#!/usr/bin/expect
set timeout 20
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST
expect {
    "password:" { send "$PASS\r"; exp_continue }
    "#" {
        # 遍历可能的目录并复制文件
        send "echo '🔍 正在查找 Web 目录...'\r"
        
        # 尝试路径 1: 宝塔 Nginx 默认
        send "if \[ -d /www/server/nginx/html \]; then cp /tmp/uploaded_index.html /www/server/nginx/html/index.html && echo '✅ 已部署到 /www/server/nginx/html'; fi\r"
        
        # 尝试路径 2: 标准 Nginx
        send "if \[ -d /usr/share/nginx/html \]; then cp /tmp/uploaded_index.html /usr/share/nginx/html/index.html && echo '✅ 已部署到 /usr/share/nginx/html'; fi\r"
        
        # 尝试路径 3: 宝塔默认站点
        send "if \[ -d /www/wwwroot/default \]; then cp /tmp/uploaded_index.html /www/wwwroot/default/index.html && echo '✅ 已部署到 /www/wwwroot/default'; fi\r"
        
        # 清理临时文件
        send "rm /tmp/uploaded_index.html\r"
        send "exit\r"
    }
}
expect eof
EOF

# 执行移动操作
echo "🔧 正在配置服务器文件..."
chmod +x move.exp
./move.exp
rm move.exp

echo "------------------------------------------------"
echo "🎉 部署完成！"
echo "请访问: http://$HOST"
echo "------------------------------------------------"
