#!/bin/bash
echo "Configuring passwordless SSH access..."
echo "You will be asked for the password (123456aA) one last time."
ssh-copy-id -i ~/.ssh/id_rsa.pub root@115.191.33.218

if [ $? -eq 0 ]; then
    echo "Success! You can now deploy without a password."
else
    echo "Something went wrong. Please check the error message above."
fi
