# Docker Permissions Setup for Jenkins

This document explains how to set up Docker permissions for Jenkins to allow it to build and push Docker images.

## Problem

When running Docker commands from Jenkins, you might encounter permission errors like:

```
permission denied while trying to connect to the Docker daemon socket at unix:///var/run/docker.sock
```

This happens because the Jenkins user doesn't have permission to access the Docker daemon socket.

## Solutions

There are three ways to solve this issue:

### 1. Add Jenkins User to Docker Group (Recommended)

This is the most secure and recommended approach:

```bash
# Add jenkins user to docker group
sudo usermod -aG docker jenkins

# Restart Jenkins service
sudo systemctl restart jenkins
```

### 2. Set Docker Socket Permissions

This is a quick solution but less secure:

```bash
# Change permissions of Docker socket
sudo chmod 666 /var/run/docker.sock
```

Note: This change will be reset when Docker restarts. To make it permanent, you can create a systemd unit file.

### 3. Configure Sudo Access for Jenkins

Allow Jenkins to run Docker commands with sudo without a password:

```bash
# Edit sudoers file
sudo visudo

# Add this line
jenkins ALL=(ALL) NOPASSWD: /usr/bin/docker
```

## Automatic Setup

We've included a script to set up Docker permissions automatically:

```bash
# Run the setup script
cd retraining_pipeline/docker
sudo ./setup_docker_permissions.sh
```

## Verification

To verify that Jenkins can run Docker commands:

```bash
# Switch to jenkins user
sudo su - jenkins

# Try running a Docker command
docker ps
```

If the command runs without errors, the permissions are set up correctly.

## Troubleshooting

1. **Docker socket not found**: Make sure Docker is installed and running.
2. **Jenkins user not found**: Make sure Jenkins is installed.
3. **Permission denied even after setup**: Restart Jenkins and Docker services.
4. **Changes not persisting after reboot**: Set up a systemd unit to apply permissions on startup.

## Security Considerations

Adding the Jenkins user to the Docker group effectively gives it root access to the host system. Make sure your Jenkins instance is secure and only trusted users have access to it.
