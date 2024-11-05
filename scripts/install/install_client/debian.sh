#!/bin/bash

# 创建 ansible 几遍
USERNAME="ansible"
SSH_DIR="/home/$USERNAME/.ssh"
AUTHORIZED_KEYS="$SSH_DIR/authorized_keys"
PUBLIC_KEY="ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIJ2Dc2Tkih86//1CBP+vC38FrkYWlV3KBNvXtSVJMuyf illuz@MacBook-Pro.local"

# 检查用户是否存在
if id "$USERNAME" &>/dev/null; then
    echo "用户 $USERNAME 已经存在。"
else
    # 创建用户并设置 home 目录及默认 shell
    useradd -m -s /bin/bash "$USERNAME"
    echo "用户 $USERNAME 创建成功。"
fi

# 创建 .ssh 目录（如果不存在）
if [ ! -d "$SSH_DIR" ]; then
    mkdir -p "$SSH_DIR"
    echo ".ssh 目录创建成功。"
fi

# 设置 .ssh 目录权限
chown "$USERNAME:$USERNAME" "$SSH_DIR"
chmod 700 "$SSH_DIR"

# 添加公钥到 authorized_keys 文件
if [ ! -f "$AUTHORIZED_KEYS" ] || ! grep -q "$PUBLIC_KEY" "$AUTHORIZED_KEYS"; then
    echo "$PUBLIC_KEY" >> "$AUTHORIZED_KEYS"
    echo "公钥添加成功。"
fi

# 设置 authorized_keys 文件权限
chown "$USERNAME:$USERNAME" "$AUTHORIZED_KEYS"
chmod 600 "$AUTHORIZED_KEYS"

echo "完成设置 ansible 用户的 SSH 公钥。"
