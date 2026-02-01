#!/bin/bash
HOST="101.42.116.50"
USER="root"
PASS="123456aA"

cat > inspect_cmd.exp <<EOF
#!/usr/bin/expect
set timeout 20
spawn ssh -o StrictHostKeyChecking=no $USER@$HOST
expect {
    "password:" { send "$PASS\r"; exp_continue }
    "#" {
        send "echo '--- /www/server/nginx/html/index.html ---'\r"
        send "head -n 5 /www/server/nginx/html/index.html\r"
        send "echo '--- /www/wwwroot/default/index.html ---'\r"
        send "head -n 5 /www/wwwroot/default/index.html\r"
        send "echo '--- Nginx Config ---'\r"
        send "grep -r 'server_name' /www/server/panel/vhost/nginx/\r"
        send "grep -r 'root' /www/server/panel/vhost/nginx/\r"
        send "cat /www/server/nginx/conf/nginx.conf | grep -A 10 'server \{'\r"
        send "exit\r"
    }
}
expect eof
EOF

chmod +x inspect_cmd.exp
./inspect_cmd.exp
rm inspect_cmd.exp
