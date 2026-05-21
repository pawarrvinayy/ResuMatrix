#!/bin/bash
set -e

echo "Starting initialization of unified MLOps environment..."

# Set up Docker socket permissions for Jenkins
echo "Setting up Docker socket permissions..."

# Detect operating system
OS=$(uname -s)

# Check if Docker socket exists
if [ ! -e /var/run/docker.sock ]; then
  echo "Warning: Docker socket not found at /var/run/docker.sock"
  echo "Make sure Docker is running and the socket is mounted to the container."
else
  # On macOS, we'll use --privileged flag instead of changing socket permissions
  if [ "$OS" = "Darwin" ]; then
    echo "Detected macOS. Will use --privileged flag instead of changing socket permissions."
  else
    # Try to change permissions on Linux
    if [ "$EUID" -ne 0 ]; then
      echo "Note: Not running as root. Docker socket permissions may need to be set manually."
      echo "You can run 'sudo chmod 666 /var/run/docker.sock' manually after container startup."
    else
      chmod 666 /var/run/docker.sock 2>/dev/null || {
        echo "Warning: Could not change Docker socket permissions even as root."
        echo "This might be due to Docker security settings or other restrictions."
      }
      echo "Docker socket permissions updated."
    fi
  fi
fi

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
  echo "Error: Docker is not running. Please start Docker and try again."
  exit 1
fi

# Create Docker volumes if they don't exist
echo "Creating Docker volumes for persistent storage..."
docker volume create jenkins_home || true
docker volume create mlflow_data || true

# Check if container already exists
if docker ps -a | grep -q unified-mlops; then
  echo "Container 'unified-mlops' already exists. Removing it..."
  docker rm -f unified-mlops
fi

# Copy requirements.txt to the current directory
echo "Copying requirements.txt..."
cp ../requirements.txt .

# Build the Docker image
echo "Building Docker image..."
docker build -t unified-mlops .

# Clean up the copied requirements.txt file
rm -f requirements.txt

# Detect operating system
OS=$(uname -s)

# Run the container
echo "Starting container..."
if [ "$OS" = "Darwin" ]; then
  # For macOS, use --privileged flag to handle Docker socket permissions
  echo "Detected macOS, using --privileged flag to handle Docker socket permissions"
  docker run -d \
    --name unified-mlops \
    --privileged \
    --restart unless-stopped \
    -p 8080:8080 \
    -p 50000:50000 \
    -p 5001:5001 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v jenkins_home:/var/jenkins_home \
    -v mlflow_data:/mlflow \
    unified-mlops
else
  # For Linux and other systems
  docker run -d \
    --name unified-mlops \
    --restart unless-stopped \
    -p 8080:8080 \
    -p 50000:50000 \
    -p 5001:5001 \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v jenkins_home:/var/jenkins_home \
    -v mlflow_data:/mlflow \
    unified-mlops
fi

# Check if container started successfully
if [ $? -eq 0 ]; then
  echo "\nContainer started successfully!\n"
  echo "Access Jenkins at http://localhost:8080"
  echo "Access MLflow at http://localhost:5001\n"

  # Wait for Jenkins to initialize and get admin password
  echo "Waiting for Jenkins to initialize (this may take a few minutes)..."

  # Try to get the admin password (retry for up to 2 minutes)
  for i in {1..12}; do
    if docker exec unified-mlops ls /var/jenkins_home/secrets/initialAdminPassword > /dev/null 2>&1; then
      JENKINS_PASSWORD=$(docker exec unified-mlops cat /var/jenkins_home/secrets/initialAdminPassword)
      echo "\nJenkins initialized! Initial admin password: $JENKINS_PASSWORD"
      break
    fi
    echo -n "."
    sleep 10
  done

  # If we couldn't get the password, provide instructions
  if [ -z "$JENKINS_PASSWORD" ]; then
    echo "\nJenkins is still initializing. You can get the initial admin password later with:"
    echo "docker exec unified-mlops cat /var/jenkins_home/secrets/initialAdminPassword"
  fi
else
  echo "\nFailed to start container. Please check the Docker logs."
fi
