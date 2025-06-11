#!/bin/bash

# coBoarding Installation Script
# Automatyczna instalacja i konfiguracja kompletnego środowiska

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

warn() {
    echo -e "${YELLOW}[WARNING] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

info() {
    echo -e "${BLUE}[INFO] $1${NC}"
}

# Check if running as root
check_root() {
    if [[ $EUID -eq 0 ]]; then
        error "This script should not be run as root for security reasons"
        exit 1
    fi
}

# Check system requirements
check_system() {
    log "Checking system requirements..."

    # Check OS
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        OS="linux"
        DISTRO=$(lsb_release -si 2>/dev/null || echo "Unknown")
        log "Detected Linux distribution: $DISTRO"
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        OS="macos"
        log "Detected macOS"
    else
        error "Unsupported operating system: $OSTYPE"
        exit 1
    fi

    # Check architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "x86_64" && "$ARCH" != "arm64" ]]; then
        error "Unsupported architecture: $ARCH"
        exit 1
    fi

    # Check RAM
    if [[ "$OS" == "linux" ]]; then
        RAM_GB=$(free -g | awk '/^Mem:/{print $2}')
    else
        RAM_GB=$(sysctl -n hw.memsize | awk '{print int($1/1024/1024/1024)}')
    fi

    if [[ $RAM_GB -lt 16 ]]; then
        warn "Recommended RAM: 64GB+. Current: ${RAM_GB}GB. Performance may be limited."
    else
        log "RAM check passed: ${RAM_GB}GB"
    fi

    # Check GPU (NVIDIA)
    if command -v nvidia-smi &> /dev/null; then
        GPU_INFO=$(nvidia-smi --query-gpu=name,memory.total --format=csv,noheader,nounits)
        log "NVIDIA GPU detected: $GPU_INFO"

        GPU_MEM=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits | head -1)
        if [[ $GPU_MEM -lt 8000 ]]; then
            warn "Recommended GPU memory: 8GB+. Current: ${GPU_MEM}MB"
        fi
    else
        warn "NVIDIA GPU not detected. CPU-only mode will be used (slower)"
    fi
}

# Install system dependencies
install_system_deps() {
    log "Installing system dependencies..."

    if [[ "$OS" == "linux" ]]; then
        # Update package list
        sudo apt update

        # Install basic dependencies
        sudo apt install -y \
            curl \
            wget \
            git \
            python3 \
            python3-pip \
            python3-venv \
            build-essential \
            software-properties-common \
            apt-transport-https \
            ca-certificates \
            gnupg \
            lsb-release \
            redis-server \
            nginx \
            libnss3 \
            libnspr4 \
            libatk1.0-0 \
            libatk-bridge2.0-0 \
            libcups2 \
            libdrm2 \
            libxkbcommon0 \
            libxcomposite1 \
            libxdamage1 \
            libxfixes3 \
            libxrandr2 \
            libgbm1 \
            libasound2 \
            libatspi2.0-0 \
            libxshmfence1 \
            libx11-xcb1 \
            libxcb-dri3-0 \
            libxcb1 \
            libxcomposite1 \
            libxcursor1 \
            libxdamage1 \
            libxext6 \
            libxfixes3 \
            libxi6 \
            libxrandr2 \
            libxrender1 \
            libxss1 \
            libxtst6 \
            libnss3 \
            libcups2 \
            libxss1 \
            libatspi2.0-0 \
            libcups2 \
            libdbus-1-3 \
            libdrm2 \
            libgbm1 \
            libxcomposite1 \
            libxdamage1 \
            libxfixes3 \
            libxkbcommon0 \
            libxrandr2 \
            libwayland-client0 \
            libwayland-egl1 \
            libwayland-server0 \
            libxshmfence1 \
            libxtst6 \
            fonts-liberation \
            libappindicator3-1 \
            libasound2 \
            libatk-bridge2.0-0 \
            libatk1.0-0 \
            libcairo2 \
            libcups2 \
            libdbus-1-3 \
            libdrm2 \
            libgbm1 \
            libgtk-3-0 \
            libnspr4 \
            libnss3 \
            libpango-1.0-0 \
            libx11-6 \
            libx11-xcb1 \
            libxcb1 \
            libxcomposite1 \
            libxcursor1 \
            libxdamage1 \
            libxext6 \
            libxfixes3 \
            libxi6 \
            libxrandr2 \
            libxrender1 \
            libxss1 \
            libxtst6 \
            xdg-utils \
            wget \
            xvfb \
            x11-apps \
            x11-xserver-utils \
            xorg

        # Install Docker if not present
        if ! command -v docker &> /dev/null; then
            log "Installing Docker..."
            curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
            echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
            sudo apt update
            sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

            # Add user to docker group
            sudo usermod -aG docker $USER
            log "Added $USER to docker group. Please log out and back in for changes to take effect."
        fi

        # Install NVIDIA Docker if GPU is present
        if command -v nvidia-smi &> /dev/null; then
            log "Installing NVIDIA Docker support..."
            distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
            curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
            curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | sudo tee /etc/apt/sources.list.d/nvidia-docker.list
            sudo apt update
            sudo apt install -y nvidia-docker2
            sudo systemctl restart docker
        fi

    elif [[ "$OS" == "macos" ]]; then
        # Check if Homebrew is installed
        if ! command -v brew &> /dev/null; then
            log "Installing Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        fi

        # Install dependencies via Homebrew
        brew install python@3.11 git redis nginx

        # Install Docker Desktop
        if ! command -v docker &> /dev/null; then
            warn "Please install Docker Desktop for Mac manually from https://docs.docker.com/desktop/mac/install/"
            read -p "Press Enter after installing Docker Desktop..."
        fi
    fi
}

# Create project structure
create_project_structure() {
    log "Creating project structure..."

    # Create main directories
    mkdir -p coboarding/{config,core/{automation,ai,integrations,storage},api/{routes,middleware},ui/{components,locales,assets},workers,data/{companies,prompts,models},tests,deployment,docs,logs,ssl,temp}

    # Create __init__.py files for Python packages
    find coboarding -type d -name "*.py" -prune -o -type d -print | while read dir; do
        if [[ "$dir" =~ ^coboarding/(core|api|ui|workers) ]]; then
            touch "$dir/__init__.py"
        fi
    done

    log "Project structure created successfully"
}

# Install Python dependencies
install_python_deps() {
    log "Setting up Python environment..."

    cd coboarding

    # Create virtual environment
    python3 -m venv venv
    source venv/bin/activate

    # Upgrade pip and setuptools
    pip install --upgrade pip setuptools wheel
    
    # Install greenlet with binary wheels
    log "Installing greenlet with binary wheels..."
    pip install --only-binary :all: greenlet
    
    # Install Playwright and its dependencies
    log "Installing Playwright and browsers..."
    pip install playwright
    python -m playwright install
    python -m playwright install-deps
    cat > requirements.txt << 'EOF'
# Web Framework
streamlit>=1.28.0
fastapi>=0.104.0
uvicorn>=0.24.0

# Automation and Browser Automation
botright>=0.4.0
playwright>=1.40.0
selenium>=4.15.0
python-dotenv>=1.0.0
beautifulsoup4>=4.12.0
lxml>=4.9.0
python-dateutil>=2.8.2

# AI & ML
transformers>=4.35.0
torch>=2.1.0
accelerate>=0.24.0
spacy>=3.7.0

# Document Processing
PyMuPDF>=1.23.0
python-docx>=0.8.11
Pillow>=10.1.0
pdfplumber>=0.9.0

# Data Storage
redis>=5.0.0
sqlalchemy>=2.0.0
alembic>=1.12.0

# Integrations
requests>=2.31.0
httpx>=0.25.0
slack-sdk>=3.23.0
google-auth>=2.23.0
google-auth-httplib2>=0.1.1
google-api-python-client>=2.108.0

# NLP
nltk>=3.8.1
textblob>=0.17.1

# Utilities
pydantic>=2.5.0
python-dotenv>=1.0.0
schedule>=1.2.0
asyncio>=3.4.3
aiofiles>=23.2.1
PyYAML>=6.0.1
python-multipart>=0.0.6

# Development
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.9.0
isort>=5.12.0
flake8>=6.1.0

# Monitoring
prometheus-client>=0.18.0
structlog>=23.2.0
EOF

    # Install Python packages
    log "Installing Python packages (this may take a while)..."
    pip install -r requirements.txt

    # Install Playwright browsers
    log "Installing Playwright browsers..."
    playwright install

    # Download spaCy models
    log "Downloading spaCy language models..."
    python -m spacy download en_core_web_sm
    python -m spacy download pl_core_news_sm || warn "Polish spaCy model failed to install"
    python -m spacy download de_core_news_sm || warn "German spaCy model failed to install"

    cd ..
}

# Install and configure Ollama
install_ollama() {
    log "Installing Ollama..."

    if [[ "$OS" == "linux" ]]; then
        curl -fsSL https://ollama.ai/install.sh | sh
    elif [[ "$OS" == "macos" ]]; then
        brew install ollama
    fi

    # Start Ollama service
    log "Starting Ollama service..."
    if [[ "$OS" == "linux" ]]; then
        sudo systemctl enable ollama
        sudo systemctl start ollama
    else
        # On macOS, start manually
        ollama serve &
        sleep 5
    fi

    # Download AI models
    log "Downloading AI models (this will take significant time and bandwidth)..."

    # Download LLaVA for visual processing
    log "Downloading LLaVA 7B model..."
    ollama pull llava:7b

    # Download Mistral for text processing
    log "Downloading Mistral 7B model..."
    ollama pull mistral:7b

    # Test model availability
    if ollama list | grep -q "llava:7b" && ollama list | grep -q "mistral:7b"; then
        log "AI models downloaded successfully"
    else
        error "Failed to download some AI models"
        exit 1
    fi
}

# Create environment configuration
create_env_config() {
    log "Creating environment configuration..."

    cd coboarding

    cat > .env << 'EOF'
# Database
REDIS_URL=redis://localhost:6379
DATA_TTL_HOURS=24

# AI Models
OLLAMA_BASE_URL=http://localhost:11434
CV_PARSER_MODEL=llava:7b
FORM_ANALYZER_MODEL=mistral:7b

# LinkedIn Integration (CONFIGURE THESE)
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret

# Communication Integrations (CONFIGURE THESE)
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token
TEAMS_WEBHOOK_URL=https://outlook.office.com/webhook/your-webhook
GMAIL_CLIENT_ID=your_gmail_client_id
GMAIL_CLIENT_SECRET=your_gmail_client_secret
WHATSAPP_TOKEN=your_whatsapp_business_token

# Business Model
MONTHLY_SUBSCRIPTION_USD=50.0
PER_CANDIDATE_USD=10.0

# Security
SECRET_KEY=$(openssl rand -hex 32)
API_KEY=$(openssl rand -hex 16)

# Supported Languages
SUPPORTED_LANGUAGES=en,pl,de

# Logging
LOG_LEVEL=INFO
LOG_FILE=/app/logs/coboarding.log

# Development
DEBUG=true
ENVIRONMENT=development
EOF

    log "Environment configuration created. Please edit .env file with your API keys."
    cd ..
}

# Create Docker configuration
create_docker_config() {
    log "Creating Docker configuration..."

    cd coboarding

    # Create Dockerfile
    cat > Dockerfile << 'EOF'
FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install --with-deps

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p logs temp data/models

# Expose ports
EXPOSE 8000 8501

# Default command
CMD ["python", "-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
EOF

    # Create docker-compose.yml
    cat > docker-compose.yml << 'EOF'
version: '3.8'

services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama
    environment:
      - OLLAMA_HOST=0.0.0.0
    restart: unless-stopped
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]

  coboarding-api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - REDIS_URL=redis://redis:6379
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - redis
      - ollama
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
      - ./temp:/app/temp
    restart: unless-stopped

  coboarding-ui:
    build: .
    command: streamlit run ui/app.py --server.port=8501 --server.address=0.0.0.0
    ports:
      - "8501:8501"
    environment:
      - REDIS_URL=redis://redis:6379
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - redis
      - ollama
      - coboarding-api
    volumes:
      - ./ui:/app/ui
      - ./data:/app/data
      - ./temp:/app/temp
    restart: unless-stopped

  cleanup-worker:
    build: .
    command: python workers/data_cleanup_worker.py
    environment:
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
    restart: unless-stopped

volumes:
  redis_data:
  ollama_data:
EOF

    # Create .dockerignore
    cat > .dockerignore << 'EOF'
.env
.git
.gitignore
README.md
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.pytest_cache/
.coverage
logs/
temp/
*.log
EOF

    cd ..
}

# Configure services
configure_services() {
    log "Configuring system services..."

    # Configure Redis
    if [[ "$OS" == "linux" ]]; then
        sudo systemctl enable redis-server
        sudo systemctl start redis-server

        # Configure Redis for production
        sudo tee /etc/redis/redis.conf.d/coboarding.conf << 'EOF'
# coBoarding Redis Configuration
maxmemory 2gb
maxmemory-policy allkeys-lru
save 900 1
save 300 10
save 60 10000
EOF
        sudo systemctl restart redis-server
    fi

    # Test Redis connection
    if redis-cli ping | grep -q "PONG"; then
        log "Redis is running and accessible"
    else
        warn "Redis connection test failed"
    fi
}

# Create startup script
create_startup_script() {
    log "Creating startup script..."

    cd coboarding

    cat > start.sh << 'EOF'
#!/bin/bash

# coBoarding Startup Script

set -e

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')] $1${NC}"
}

error() {
    echo -e "${RED}[ERROR] $1${NC}"
}

# Check if .env exists
if [[ ! -f .env ]]; then
    error ".env file not found. Please run install.sh first."
    exit 1
fi

# Source environment
source .env

# Activate virtual environment
if [[ -d venv ]]; then
    source venv/bin/activate
    log "Activated Python virtual environment"
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags >/dev/null; then
    log "Starting Ollama service..."
    if command -v systemctl >/dev/null 2>&1; then
        sudo systemctl start ollama
    else
        ollama serve &
    fi
    sleep 5
fi

# Check if models are available
log "Checking AI models..."
if ! ollama list | grep -q "llava:7b"; then
    log "Downloading LLaVA model..."
    ollama pull llava:7b
fi

if ! ollama list | grep -q "mistral:7b"; then
    log "Downloading Mistral model..."
    ollama pull mistral:7b
fi

# Start services with Docker Compose
log "Starting coBoarding services..."
docker-compose up -d

# Wait for services to be ready
log "Waiting for services to start..."
sleep 10

# Check service health
log "Checking service health..."
if curl -s http://localhost:8000/health >/dev/null; then
    log "✅ API service is healthy"
else
    error "❌ API service is not responding"
fi

if curl -s http://localhost:8501 >/dev/null; then
    log "✅ UI service is healthy"
else
    error "❌ UI service is not responding"
fi

log "🚀 coBoarding is ready!"
log "📊 API: http://localhost:8000"
log "🖥️  UI: http://localhost:8501"
log "📝 Logs: docker-compose logs -f"
EOF

    chmod +x start.sh

    cd ..
}

# Create stop script
create_stop_script() {
    cd coboarding

    cat > stop.sh << 'EOF'
#!/bin/bash

# coBoarding Stop Script

log() {
    echo -e "\033[0;32m[$(date +'%Y-%m-%d %H:%M:%S')] $1\033[0m"
}

log "Stopping coBoarding services..."
docker-compose down

log "Services stopped successfully"
EOF

    chmod +x stop.sh

    cd ..
}

# Run health checks
health_check() {
    log "Running system health checks..."

    cd coboarding

    # Check Python environment
    if source venv/bin/activate && python --version >/dev/null 2>&1; then
        log "✅ Python environment OK"
    else
        error "❌ Python environment failed"
    fi

    # Check Redis
    if redis-cli ping | grep -q "PONG"; then
        log "✅ Redis OK"
    else
        error "❌ Redis failed"
    fi

    # Check Ollama
    if curl -s http://localhost:11434/api/tags >/dev/null; then
        log "✅ Ollama OK"
    else
        warn "⚠️  Ollama not running (will be started automatically)"
    fi

    # Check Docker
    if docker --version >/dev/null 2>&1; then
        log "✅ Docker OK"
    else
        error "❌ Docker failed"
    fi

    cd ..
}

# Create README
create_readme() {
    log "Creating README..."

    cd coboarding

    cat > README.md << 'EOF'
# coBoarding - AI-Powered Job Application Automation

Automated job application platform with AI-powered CV parsing and form filling.

## Quick Start

```bash
# Start all services
./start.sh

# Access the application
open http://localhost:8501

# Stop services
./stop.sh
```

## Services

- **UI**: http://localhost:8501 (Streamlit)
- **API**: http://localhost:8000 (FastAPI)
- **Redis**: localhost:6379
- **Ollama**: http://localhost:11434

## Configuration

1. Edit `.env` file with your API keys
2. Configure LinkedIn Developer App
3. Set up payment processing
4. Add company integrations

## Documentation

- Setup: `docs/setup.md`
- API: `docs/api.md`
- Compliance: `docs/compliance.md`

## Support

For issues and questions, check the logs:
```bash
docker-compose logs -f
```
EOF

    cd ..
}

# Main installation function
main() {
    log "🚀 Starting coBoarding installation..."

    check_root
    check_system
    install_system_deps
    create_project_structure
    install_python_deps
    install_ollama
    create_env_config
    create_docker_config
    configure_services
    create_startup_script
    create_stop_script
    health_check
    create_readme

    log "✅ Installation completed successfully!"
    echo ""
    info "📋 Next steps:"
    info "1. cd coboarding"
    info "2. Edit .env file with your API keys"
    info "3. Run: ./start.sh"
    info "4. Open: http://localhost:8501"
    echo ""
    warn "⚠️  Important: Configure your LinkedIn Developer App and payment processing before production use"
}

# Run main function
main "$@"