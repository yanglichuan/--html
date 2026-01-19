#!/bin/bash

# 配置信息
REMOTE_IP="115.191.33.218"
REMOTE_USER="root"
REMOTE_WEB_ROOT="/usr/share/nginx/html"
BACKEND_FILES=("server.js" "package.json")
BACKEND_PATH="/root/stock-backend"

echo "🚀 开始上传前端文件到服务器 $REMOTE_IP..."
# 上传主文件并设为默认 index.html
scp ./gupiao_new.html $REMOTE_USER@$REMOTE_IP:$REMOTE_WEB_ROOT/index.html
# 上传火山版文件
scp ./gupiao_new_huoshan.html $REMOTE_USER@$REMOTE_IP:$REMOTE_WEB_ROOT/huoshan.html

echo "🚀 开始同步后端文件..."
ssh $REMOTE_USER@$REMOTE_IP "mkdir -p $BACKEND_PATH"
for file in "${BACKEND_FILES[@]}"; do
    scp "./$file" "$REMOTE_USER@$REMOTE_IP:$BACKEND_PATH/"
done

echo "🚀 开始上传 Nginx 配置文件..."
scp ./nginx.conf $REMOTE_USER@$REMOTE_IP:/etc/nginx/nginx.conf
ssh $REMOTE_USER@$REMOTE_IP "systemctl restart nginx"

if [ $? -eq 0 ]; then
    echo "✅ 文件上传成功！"
    echo "------------------------------------------------"
    echo "📌 下一步操作（在服务器上执行）："
    echo "1. 进入目录: cd $BACKEND_PATH"
    echo "2. 安装 Node.js (如果没装): curl -fsSL https://rpm.nodesource.com/setup_18.x | bash - && yum install -y nodejs"
    echo "3. 安装依赖: npm install"
    echo "4. 安装 pm2 并启动: npm install -g pm2 && pm2 start server.js --name stock-backend"
    echo "5. 配置 Nginx 反向代理: 编辑 /etc/nginx/nginx.conf，在 server 块添加："
    echo "   location /api/ { proxy_pass http://127.0.0.1:3000; }"
    echo "6. 重启 Nginx: systemctl restart nginx"
    echo "------------------------------------------------"
    echo "🌐 部署完成后访问: http://$REMOTE_IP"
else
    echo "❌ 上传失败，请检查密码或网络连接。"
fi
