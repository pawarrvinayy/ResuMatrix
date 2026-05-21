FROM jenkins/jenkins:lts

USER root

# Install system dependencies and clean up in a single layer
RUN apt-get update && apt-get install -y \
    python3 python3-pip python3-venv python3-full \
    docker.io curl apt-transport-https ca-certificates gnupg jq sudo \
    && rm -rf /var/lib/apt/lists/* \
    && curl -L "https://github.com/docker/compose/releases/download/v2.20.3/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose \
    && chmod +x /usr/local/bin/docker-compose \
    && usermod -aG docker jenkins \
    && echo "jenkins ALL=(ALL) NOPASSWD: /usr/bin/docker, /usr/bin/chmod" >> /etc/sudoers \
    && python3 -m venv /opt/venv

# Install Google Cloud SDK
RUN echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# Set Python environment path
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements.txt and install Python dependencies
COPY requirements.txt /tmp/requirements.txt
RUN /opt/venv/bin/pip install --upgrade pip \
    && /opt/venv/bin/pip install --no-cache-dir -r /tmp/requirements.txt \
    && /opt/venv/bin/pip install --no-cache-dir mlflow==2.8.1 google-cloud-storage

# Create directories and set permissions
RUN mkdir -p /mlflow/artifacts /mlflow/mlruns /var/log/supervisor \
    && chown -R jenkins:jenkins /mlflow /opt/venv \
    && chmod -R 755 /var/log/supervisor

# Install Jenkins plugins
RUN jenkins-plugin-cli --plugins \
    workflow-aggregator git docker-workflow email-ext \
    credentials-binding pipeline-utility-steps \
    google-oauth-plugin google-storage-plugin google-compute-engine \
    github github-branch-source github-api

# Copy startup script
COPY start-services.sh /usr/local/bin/start-services.sh
RUN chmod +x /usr/local/bin/start-services.sh

# Set environment variables
ENV MLFLOW_TRACKING_URI=http://localhost:5001
ENV JENKINS_UC_DOWNLOAD=https://updates.jenkins.io/download

# Switch back to jenkins user
USER jenkins

# Expose ports for Jenkins and MLflow
EXPOSE 8080 50000 5001

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
  CMD curl -f http://localhost:8080/ || curl -f http://localhost:5001/ || exit 1

# Start services
ENTRYPOINT ["/usr/local/bin/start-services.sh"]
