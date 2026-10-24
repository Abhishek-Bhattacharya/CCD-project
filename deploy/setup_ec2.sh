#!/bin/bash
# One-time initialization script for single Ubuntu 22.04 / 24.04 LTS EC2 Instance
set -euo pipefail

echo "=== [PhoenixCI] Initializing Ubuntu EC2 Instance ==="

# Update package repository
sudo apt-get update -y
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Install Docker Engine if not present
if ! command -v docker &> /dev/null; then
    echo "Installing Docker..."
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
      $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -y
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    sudo usermod -aG docker ubuntu
fi

# Ensure workspace directory exists
mkdir -p ~/phoenixci/deploy ~/phoenixci/state

# Create initial state file
echo "initial" > ~/phoenixci/state/active_version.txt

echo "=== [PhoenixCI] EC2 Environment Ready ==="
