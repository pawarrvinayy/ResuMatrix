#!/bin/bash

set -e

echo "Starting setup..."

# --------- Detect OS ---------
OS_TYPE="$(uname || true)"  # '|| true' prevents exit on failure
echo "OS detected: $OS_TYPE"

# Check if Docker is installed
if command -v docker >/dev/null 2>&1; then
    IS_DOCKER_INSTALLED=true
else
    IS_DOCKER_INSTALLED=false
fi

# --------- Install Docker on Linux ---------
install_docker_linux() {
    echo "Installing Docker on Linux..."
    sudo apt update
    sudo apt install -y \
        ca-certificates \
        curl \
        gnupg \
        lsb-release

    sudo mkdir -p /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg

    echo \
      "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
      https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
      sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt update
    sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

    sudo usermod -aG docker $USER
    echo "Docker installed on Linux! Please restart your terminal to apply permissions."
}

# --------- Install Docker on macOS using Homebrew ---------
install_docker_macos() {
    echo "Installing Docker on macOS via Homebrew..."

    if ! command -v brew >/dev/null 2>&1; then
        echo "Homebrew not found. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    brew install --cask docker

    echo "Docker installed! Please open Docker.app manually to complete the setup and accept permissions."
    echo "Docker daemon must be started manually at least once (Applications > Docker)."
}

# --------- Install Docker on Windows using winget ---------
install_docker_windows() {
    echo "Installing Docker Desktop on Windows via winget..."

    if ! command -v winget >/dev/null 2>&1; then
        echo "winget not found. Please install Docker Desktop manually: https://www.docker.com/products/docker-desktop"
        exit 1
    fi

    echo "Installing Docker Desktop..."
    winget install -e --id Docker.DockerDesktop --accept-package-agreements --accept-source-agreements

    echo "Docker Desktop installed! Please launch it manually once to finish setup and enable WSL2 integration."
    echo "Restart terminal after Docker Desktop is launched."
}

# --------- Docker Checks and Setup ---------
if [ "$IS_DOCKER_INSTALLED" = "false" ]; then
    if [[ "$OS_TYPE" == "Linux" ]]; then
        install_docker_linux
    elif [[ "$OS_TYPE" == "Darwin" ]]; then
        install_docker_macos
    elif [[ "$OS_TYPE" == "NT" || "$OS_TYPE" == "MINGW"* || "$OS_TYPE" == "CYGWIN"* ]]; then
        install_docker_windows
    else
        echo "Unsupported OS: $OS_TYPE"
        exit 1
    fi
else
    echo "Docker is already installed!"
fi

# --------- Verify Docker Daemon Running ---------
if ! docker info >/dev/null 2>&1; then
    echo "Docker is installed but the daemon is not running. Attempting to start Docker..."

    if [[ "$OS_TYPE" == "Linux" ]]; then
        echo "🔧 Trying to start Docker service on Linux..."
        sudo systemctl start docker

        sleep 3  # Give it a moment to initialize

        if docker info >/dev/null 2>&1; then
            echo "Docker daemon started successfully!"
        else
            echo "Failed to start Docker daemon on Linux. Please check systemctl logs."
            exit 1
        fi

    elif [[ "$OS_TYPE" == "Darwin" ]]; then
        echo "Trying to start Docker on macOS (via Docker.app)..."
        # open -a Docker
        if [ -e "/Applications/Docker.app" ]; then
            open "/Applications/Docker.app"
        else
            echo "Docker.app not found in /Applications. Please install Docker Desktop manually: https://www.docker.com/products/docker-desktop"
            exit 1
        fi


        echo "Waiting for Docker to start..."
        retries=0
        until docker info >/dev/null 2>&1 || [ $retries -ge 20 ]; do
            sleep 2
            ((retries++))
        done

        if docker info >/dev/null 2>&1; then
            echo "Docker is now running on macOS!"
        else
            echo "Docker did not start within expected time on macOS. Please open Docker manually."
            exit 1
        fi

    elif [[ "$OS_TYPE" == "NT" || "$OS_TYPE" == "MINGW"* || "$OS_TYPE" == "CYGWIN"* ]]; then
        echo "Cannot automatically start Docker Desktop on Windows via script."
        echo "Please launch Docker Desktop manually and ensure WSL2 backend is enabled."
        exit 1
    else
        echo "Unsupported OS for auto-start: $OS_TYPE"
        exit 1
    fi
else
    echo "Docker daemon is running!"
fi

# Clone your GitHub repo
REPO_URL="https://github.com/ResuMatrix/ResuMatrix.git"
CLONE_DIR="$HOME/ResuMatrix"

if [ ! -d "$CLONE_DIR" ]; then
    echo "Cloning repository..."
    git clone "$REPO_URL" "$CLONE_DIR"
else
    echo "Repository already exists at $CLONE_DIR"
fi

cd "$CLONE_DIR"


echo "Setup completed!"