#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"

cat > get_info.exp <<EOF
#!/usr/bin/expect
set timeout 20
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST
expect {
    "password:" { send "$PASS\r"; exp_continue }
    "#" {
        send "echo '----------------------------------------'\r"
        send "echo '1️⃣  Nginx 程序位置:'\r"
        send "ls -lh /www/server/nginx/sbin/nginx\r"
        
        send "echo '\r\n2️⃣  配置文件位置:'\r"
        send "echo '主配置文件: /www/server/nginx/conf/nginx.conf'\r"
        send "echo '子配置目录 (vhost): /www/server/panel/vhost/nginx/'\r"
        send "ls -lh /www/server/panel/vhost/nginx/\r"
        
        send "echo '\r\n3️⃣  网页文件目录 (HTML):'\r"
        send "echo '当前使用的目录: /www/server/nginx/html/'\r"
        send "ls -lh /www/server/nginx/html/\r"
        
        send "echo '\r\n4️⃣  日志文件目录:'\r"
        send "echo '日志存放处: /www/wwwlogs/'\r"
        send "ls -lh /www/wwwlogs/ | head -n 5\r"
        
        send "exit\r"
    }
}
expect eof
EOF

chmod +x get_info.exp
./get_info.exp
rm get_info.exp
