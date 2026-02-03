#!/bin/bash
set -e

# 颜色定义
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m'

echo -e "${BLUE}=== 开始 Hexo 一键部署 ===${NC}"

# 确保在脚本所在目录
cd "$(dirname "$0")"

# 清理并生成
echo -e "${BLUE}[1/2] 清理并生成静态文件...${NC}"
npx hexo clean
npx hexo g

# 部署到服务器
echo -e "${BLUE}[2/2] 正在上传到服务器 (101.42.116.50)...${NC}"
sshpass -p "123456aA" scp -o StrictHostKeyChecking=no -r public/* root@101.42.116.50:/www/server/nginx/html/hexo/

echo -e "${GREEN}=== 部署成功! ===${NC}"
echo -e "${GREEN}访问地址: http://101.42.116.50/hexo/${NC}"
