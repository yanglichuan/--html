#!/bin/bash

# 配置信息
REMOTE_IP="115.191.33.218"
REMOTE_USER="root"
LOCAL_FILE="gupiao_new.html"
REMOTE_PATH="/usr/share/nginx/html/index.html"

echo "🚀 开始上传 $LOCAL_FILE 到服务器 $REMOTE_IP..."

# 使用 scp 上传
# 注意：如果远程目录不存在，或者没有安装 nginx，可能需要先执行服务器配置
scp ./$LOCAL_FILE $REMOTE_USER@$REMOTE_IP:$REMOTE_PATH

if [ $? -eq 0 ]; then
    echo "✅ 上传成功！"
    echo "🌐 请访问: http://$REMOTE_IP"
else
    echo "❌ 上传失败，请检查密码或网络连接。"
fi
