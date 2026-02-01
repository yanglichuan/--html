#!/bin/bash

# 获取脚本所在目录的绝对路径
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
PROJECT_ROOT="$SCRIPT_DIR/media_server"

echo "🚀 Starting Media Server..."

# 检查是否安装了依赖
if ! pip3 show fastapi > /dev/null 2>&1; then
    echo "📦 Installing dependencies..."
    pip3 install -r "$PROJECT_ROOT/requirements.txt"
fi

# 检查端口 8005 是否被占用，如果占用则杀掉
PID=$(lsof -ti:8005)
if [ ! -z "$PID" ]; then
    echo "⚠️  Port 8005 is busy. Killing process $PID..."
    kill -9 $PID
fi

# 启动服务 (后台运行)
echo "🔥 Launching server..."
cd "$PROJECT_ROOT"
# 使用 nohup 后台运行，并将日志重定向
nohup python3 main.py > server.log 2>&1 &
SERVER_PID=$!

# 等待服务启动
echo "⏳ Waiting for server to be ready..."
max_retries=30
count=0
while ! nc -z localhost 8005; do   
  sleep 0.5
  count=$((count+1))
  if [ $count -ge $max_retries ]; then
      echo "❌ Server failed to start within timeout."
      echo "Check logs at $PROJECT_ROOT/server.log"
      exit 1
  fi
done

echo "✅ Server is up and running (PID: $SERVER_PID)"

# 获取本机局域网 IP
LOCAL_IP=$(ipconfig getifaddr en0 || ipconfig getifaddr en1)

echo "---------------------------------------------------"
echo "🌐 Local Access:   http://localhost:8005"
if [ ! -z "$LOCAL_IP" ]; then
    echo "📡 Network Access: http://$LOCAL_IP:8005"
    echo "   (Share this link with devices in the same WiFi)"
fi
echo "---------------------------------------------------"

# 打开浏览器
echo "🚀 Opening browser..."
open "http://localhost:8005"

echo "🎉 Done! Press Ctrl+C to stop the server if running in foreground (or use 'kill $SERVER_PID' to stop background process)"
