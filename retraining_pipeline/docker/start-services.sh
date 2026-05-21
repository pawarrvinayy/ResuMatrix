#!/bin/bash
set -e

# Ensure directories exist with proper permissions
mkdir -p /mlflow/artifacts /mlflow/mlruns /var/log/supervisor
chown -R jenkins:jenkins /mlflow

# Check if we're running in a privileged container
if grep -q "privileged" /proc/self/status 2>/dev/null; then
  echo "Running in a privileged container, no need to change Docker socket permissions."
else
  # Ensure Docker socket has correct permissions
  if [ -e /var/run/docker.sock ]; then
    echo "Checking Docker socket permissions..."
    # Try to change permissions, but don't fail if it doesn't work
    chmod 666 /var/run/docker.sock 2>/dev/null || {
      echo "Warning: Could not change Docker socket permissions. Container will continue, but Docker commands may fail."
      echo "This is expected on macOS. The container should still work if started with --privileged."
    }
  else
    echo "Warning: Docker socket not found at /var/run/docker.sock"
  fi
fi

# Start MLflow in the background
echo "Starting MLflow server on port 5001..."
cd /mlflow && /opt/venv/bin/mlflow server \
  --host 0.0.0.0 \
  --port 5001 \
  --backend-store-uri /mlflow/mlruns \
  --default-artifact-root /mlflow/artifacts &

# Start Jenkins in the foreground
echo "Starting Jenkins server..."
exec /usr/local/bin/jenkins.sh
