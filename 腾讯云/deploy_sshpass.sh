#!/bin/bash

# 服务器信息
HOST="101.42.116.50"
USER="root"
PASS="123456aA"

# 1. 本地源文件 (必选)
LOCAL_FILE="${1:-index.html}"

# 2. 远程文件名 (可选，如果不传则使用本地文件名)
# 如果用户想覆盖首页，可以传 index.html
if [ -n "$2" ]; then
    REMOTE_FILENAME="$2"
else
    # 提取文件名 (例如 /path/to/foo.html -> foo.html)
    REMOTE_FILENAME=$(basename "$LOCAL_FILE")
fi

# 检查文件是否存在
if [ ! -f "$LOCAL_FILE" ]; then
    echo "❌ 错误: 文件 '$LOCAL_FILE' 不存在！"
    echo "用法: ./deploy_sshpass.sh [本地文件] [远程文件名(可选)]"
    exit 1
fi

# 定义远程命令
REMOTE_CMD="
TARGET_DIR='/www/server/nginx/html'

echo '=== 开始部署 ==='
if [ -d \$TARGET_DIR ]; then 
    mv /tmp/uploaded_file \$TARGET_DIR/$REMOTE_FILENAME
    echo '✅ 已部署: $REMOTE_FILENAME'
    echo '📂 路径: ' \$TARGET_DIR/$REMOTE_FILENAME
else
    echo '❌ 严重错误: 未找到 Web 目录 /www/server/nginx/html'
fi
"

echo "🚀 开始部署 '$LOCAL_FILE' 到腾讯云 ($HOST)..."
echo "📄 目标文件名: $REMOTE_FILENAME"

# 1. 使用 sshpass 上传文件
echo "📤 正在上传文件..."
sshpass -p "$PASS" scp -o StrictHostKeyChecking=no "$LOCAL_FILE" $USER@$HOST:/tmp/uploaded_file

# 2. 使用 sshpass 执行远程命令
echo "🔧 正在更新服务器文件..."
sshpass -p "$PASS" ssh -o StrictHostKeyChecking=no $USER@$HOST "$REMOTE_CMD"

echo "------------------------------------------------"
echo "🎉 部署完成！"
echo "请访问: http://$HOST/$REMOTE_FILENAME"
echo "------------------------------------------------"
