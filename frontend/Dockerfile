# Use a slim Python image
FROM python:3.13-slim-bookworm

# Install curl and certs for downloading uv
RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates libmagic1

# Install uv
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Ensure the installed binary is on the `PATH`
ENV PATH="/root/.local/bin/:$PATH"

# Add your frontend code
ADD . /streamlit_app

WORKDIR /streamlit_app

# Install frontend dependencies
RUN uv sync --frozen

ENV PATH="/streamlit_app/.venv/bin:$PATH"

# Expose Streamlit's default port
EXPOSE 8501

# Run the Streamlit app
CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
