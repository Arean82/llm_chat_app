#!/bin/bash
# Auto-generated installer for synora-test-service-linux
set -e

echo "=== Installing synora-test-service-linux ==="

if ! id "root" &>/dev/null; then
    echo "Creating dedicated service user: root"
    useradd -r -s /usr/sbin/nologin root
else
    echo "User root already exists."
fi

echo "Creating Log and Environment Directories..."
mkdir -p /var/log/synora-test-service-linux
mkdir -p $(dirname /etc/synora-test-service-linux/.env)
touch /etc/synora-test-service-linux/.env

echo "Applying strict ownership to root:root..."
chown -R root:root /var/log/synora-test-service-linux
chown -R root:root c:\Users\user\OneDrive\Desktop\python\llm_chat_app
chown root:root /etc/synora-test-service-linux/.env
chmod 600 /etc/synora-test-service-linux/.env

echo "Installing systemd service file..."
cp synora-test-service-linux.service /etc/systemd/system/
systemctl daemon-reload

systemctl enable --now synora-test-service-linux

echo "✅ Installation complete! Check logs using: journalctl -u synora-test-service-linux -f"