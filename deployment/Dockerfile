# Use Python 3.11 as the base image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    git \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Playwright dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgtk-3-0 \
    libnotify-dev \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libxtst6 \
    xvfb \
    fonts-liberation \
    libappindicator3-1 \
    lsb-release \
    xdg-utils \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Install Node.js for Playwright
RUN curl -sL https://deb.nodesource.com/setup_18.x | bash - \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Create a minimal requirements file for container
RUN echo "fastapi==0.110.0" > container_requirements.txt && \
    echo "uvicorn==0.27.1" >> container_requirements.txt && \
    echo "python-multipart==0.0.9" >> container_requirements.txt && \
    echo "python-dotenv==1.0.1" >> container_requirements.txt && \
    echo "pydantic==2.6.4" >> container_requirements.txt && \
    echo "playwright==1.43.0" >> container_requirements.txt

# Install minimal Python dependencies
RUN pip install --no-cache-dir -r container_requirements.txt

# Install Playwright browsers
RUN npx playwright install-deps
RUN npx playwright install chromium

# Copy the rest of the application
COPY . .

# Install the package in development mode
RUN pip install -e .

# Set the default command to run the API server
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
