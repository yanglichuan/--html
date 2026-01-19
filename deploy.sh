#!/bin/bash

# 配置信息
REMOTE_IP="115.191.33.218"
REMOTE_USER="root"
REMOTE_WEB_ROOT="/usr/share/nginx/html"
BACKEND_FILES=("server.js" "package.json")
BACKEND_PATH="/root/stock-backend"
CLOUD_PATH="/root/cloud-control"

echo "🚀 开始上传前端文件到服务器 $REMOTE_IP..."
# 上传主文件并设为默认 index.html
scp ./gupiao_new.html $REMOTE_USER@$REMOTE_IP:$REMOTE_WEB_ROOT/index.html

echo "🚀 开始同步用户系统后端文件..."
ssh $REMOTE_USER@$REMOTE_IP "mkdir -p $BACKEND_PATH"
for file in "${BACKEND_FILES[@]}"; do
    scp "./$file" "$REMOTE_USER@$REMOTE_IP:$BACKEND_PATH/"
done

echo "🚀 开始同步云控系统后端文件..."
ssh $REMOTE_USER@$REMOTE_IP "mkdir -p $CLOUD_PATH/public"
scp ./cloud-control/server.js $REMOTE_USER@$REMOTE_IP:$CLOUD_PATH/
scp ./cloud-control/package.json $REMOTE_USER@$REMOTE_IP:$CLOUD_PATH/
scp ./cloud-control/public/index.html $REMOTE_USER@$REMOTE_IP:$CLOUD_PATH/public/

echo "🚀 开始上传 Nginx 配置文件..."
scp ./nginx.conf $REMOTE_USER@$REMOTE_IP:/etc/nginx/nginx.conf
ssh $REMOTE_USER@$REMOTE_IP "systemctl restart nginx"

if [ $? -eq 0 ]; then
    echo "✅ 文件上传成功！"
    echo "------------------------------------------------"
    echo "📌 首次部署说明（在服务器上执行）："
    echo "1. 安装环境 (Node.js):"
    echo "   curl -fsSL https://rpm.nodesource.com/setup_18.x | bash - && yum install -y nodejs"
    echo ""
    echo "2. 启动用户系统:"
    echo "   cd $BACKEND_PATH && npm install && pm2 start server.js --name stock-user"
    echo ""
    echo "3. 启动云控系统:"
    echo "   cd $CLOUD_PATH && npm install && pm2 start server.js --name cloud-control"
    echo ""
    echo "4. 保存 PM2 状态 (重启服务器自动运行):"
    echo "   pm2 save && pm2 startup"
    echo "------------------------------------------------"
    echo "🌐 访问地址:"
    echo "👉 股票系统: http://$REMOTE_IP"
    echo "👉 云控管理: http://$REMOTE_IP/cloud/"
    echo "👉 云控 API: http://$REMOTE_IP/api/config/{key}"
    echo "------------------------------------------------"
else
    echo "❌ 上传失败，请检查密码或网络连接。"
fi
