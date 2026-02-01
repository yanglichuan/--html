#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"

cat > deep_inspect.exp <<EOF
#!/usr/bin/expect
set timeout 20
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST
expect {
    "password:" { send "$PASS\r"; exp_continue }
    "#" {
        send "echo '=== Nginx Conf ==='\r"
        send "cat /www/server/nginx/conf/nginx.conf\r"
        send "echo '=== Vhost Directory ==='\r"
        send "ls -la /www/server/panel/vhost/nginx/\r"
        send "echo '=== Default Site Config ==='\r"
        send "cat /www/server/panel/vhost/nginx/0.default.conf\r"
        send "cat /www/server/panel/vhost/nginx/default.conf\r"
        send "exit\r"
    }
}
expect eof
EOF

chmod +x deep_inspect.exp
./deep_inspect.exp
rm deep_inspect.exp
