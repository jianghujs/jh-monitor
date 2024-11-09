import os
import socket
import subprocess
import json

def get_ssh_login_record():
    log_file_path = '/var/log/auth.log'
    ssh_login_attempts = []

    with open(log_file_path, 'r') as log_file:
        for line in log_file:
            # 示例正则表达式，用于匹配 SSH 登录尝试
            match = re.search(r'sshd\[.*\]: Accepted .* for (.+) from (\d+\.\d+\.\d+\.\d+) port', line)
            if match:
                user = match.group(1)
                ip_address = match.group(2)
                ssh_login_attempts.append({
                  "user": user, 
                  "ip": ip_address, 
                  "log": line.strip()
                })

    return ssh_login_attempts

def get_ssh_cmd_record():
    user_home_directory = '/root' 
    bash_history_path = os.path.join(user_home_directory, '.bash_history')
    if not os.path.exists(bash_history_path):
        print(f"No .bash_history file found for {user_home_directory}")
        return []

    with open(bash_history_path, 'r') as history_file:
        return history_file.readlines()

def main():
    ssh_info = {
        "sshLoginRecord": get_ssh_login_record(),
        "sshCmdRecord": get_ssh_cmd_record()
    }
    
    # 将字典转换为 JSON 格式的字符串并打印
    print(json.dumps(ssh_info))


if __name__ == '__main__':
    main()
