#!/bin/bash

# coBoarding Installation Script for Fedora
# Complete installation and configuration of the development environment

set -e  # Exit on any error
set -o pipefail  # Exit on pipe failures

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
    if [[ -f /etc/fedora-release ]]; then
        OS="fedora"
        DISTRO=$(cat /etc/fedora-release)
        log "Detected Linux distribution: $DISTRO"
        
        # Check Fedora version
        FEDORA_VERSION=$(rpm -E %fedora)
        if [[ $FEDORA_VERSION -lt 37 ]]; then
            warn "Fedora $FEDORA_VERSION is not officially supported. Some features may not work correctly."
        fi
    else
        error "This script is intended for Fedora Linux only"
        exit 1
    fi

    # Check architecture
    ARCH=$(uname -m)
    if [[ "$ARCH" != "x86_64" && "$ARCH" != "arm64" ]]; then
        error "Unsupported architecture: $ARCH"
        exit 1
    fi

    # Check RAM
    RAM_GB=$(free -g | awk '/^Mem:/{print $2}')

    if [[ $RAM_GB -lt 16 ]]; then
        warn "Recommended RAM: 16GB+. Current: ${RAM_GB}GB. Performance may be limited."
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

    # Enable RPM Fusion repositories
    if ! rpm -q rpmfusion-free-release &> /dev/null; then
        log "Enabling RPM Fusion repositories..."
        sudo dnf install -y https://download1.rpmfusion.org/free/fedora/rpmfusion-free-release-$(rpm -E %fedora).noarch.rpm
        sudo dnf install -y https://download1.rpmfusion.org/nonfree/fedora/rpmfusion-nonfree-release-$(rpm -E %fedora).noarch.rpm
    fi

    # Update package list
    sudo dnf update -y

    # Install Python 3.11 if not present
    if ! command -v python3.11 &> /dev/null; then
        log "Installing Python 3.11..."
        sudo dnf install -y python3.11 python3.11-devel python3.11-pip python3.11-venv
        sudo alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1
        sudo alternatives --set python3 /usr/bin/python3.11
    fi

    # Install basic dependencies
    log "Installing system dependencies..."
    sudo dnf install -y \
        curl \
        wget \
        git \
        gcc \
        gcc-c++ \
        make \
        redhat-lsb-core \
        ca-certificates \
        nginx \
        redis \
        nodejs \
        npm \
        libffi-devel \
        openssl-devel \
        bzip2-devel \
        readline-devel \
        sqlite-devel \
        tk-devel \
        xz-devel \
        cmake \
        pkg-config \
        libxkbcommon-x11 \
        libxkbcommon \
        libXcomposite \
        libXdamage \
        libXrandr \
        libgbm \
        libpango-1.0-0 \
        libcairo2 \
        libatk1.0-0 \
        libatk-bridge2.0-0 \
        libdrm \
        libxshmfence \
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
        @development-tools

    # Install Node.js 18.x if not present
    if ! command -v node &> /dev/null || [[ $(node --version | cut -d'v' -f2 | cut -d'.' -f1) -lt 18 ]]; then
        log "Installing Node.js 18.x..."
        curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
        sudo dnf install -y nodejs
        
        # Install required global npm packages
        sudo npm install -g npm@latest
        sudo npm install -g playwright
    fi

    # Install Chromium dependencies
    log "Installing Chromium dependencies..."
    sudo dnf install -y \
        alsa-lib \
        atk \
        at-spi2-atk \
        cups-libs \
        gtk3 \
        libXcomposite \
        libXcursor \
        libXdamage \
        libXext \
        libXfixes \
        libXi \
        libXrandr \
        libXScrnSaver \
        libXtst \
        pango \
        xorg-x11-fonts-100dpi \
        xorg-x11-fonts-75dpi \
        xorg-x11-fonts-cyrillic \
        xorg-x11-fonts-misc \
        xorg-x11-fonts-Type1 \
        xorg-x11-utils

    # Install Docker if not present
    if ! command -v docker &> /dev/null; then
        log "Installing Docker..."
        sudo dnf -y install dnf-plugins-core
        sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
        sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
        
        # Start and enable Docker
        sudo systemctl start docker
        sudo systemctl enable docker
        
        # Add user to docker group
        sudo usermod -aG docker $USER
        log "Added $USER to docker group. Please log out and back in for changes to take effect."
    fi

    # Install NVIDIA Docker if GPU is present
    if command -v nvidia-smi &> /dev/null; then
        log "Installing NVIDIA Container Toolkit..."
        distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
        
        # Install NVIDIA Container Toolkit
        sudo dnf config-manager --add-repo https://nvidia.github.io/libnvidia-container/stable/rpm/nvidia-container-toolkit.repo
        sudo dnf clean all
        sudo dnf install -y nvidia-container-toolkit
        
        # Configure Docker to use NVIDIA runtime
        sudo nvidia-ctk runtime configure --runtime=docker
        sudo systemctl restart docker
        
        log "NVIDIA Container Toolkit installed successfully"
    fi
}

# Setup Python virtual environment
setup_python_env() {
    log "Setting up Python virtual environment..."
    
    # Create virtual environment if it doesn't exist
    if [[ ! -d "venv" ]]; then
        python3.11 -m venv venv
    fi
    
    # Activate virtual environment
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
    
    # Install other Python dependencies
    if [[ -f "requirements.txt" ]]; then
        log "Installing Python dependencies from requirements.txt..."
        pip install -r requirements.txt
    else
        warn "requirements.txt not found. Installing common dependencies..."
        pip install \
            numpy pandas scipy scikit-learn \
            flask fastapi uvicorn python-multipart \
            python-dotenv pyyaml \
            selenium playwright \
            python-jose[cryptography] passlib[bcrypt] \
            python-multipart email-validator \
            sqlalchemy alembic psycopg2-binary \
            redis celery[redis] \
            python-dateutil pytz \
            requests beautifulsoup4 lxml \
            pillow opencv-python-headless \
            tqdm loguru
    fi
    
    # Install Playwright browsers
    log "Installing Playwright browsers..."
    playwright install --with-deps
    
    # Install development tools
    pip install black flake8 mypy isort pytest pytest-cov
    
    log "Python environment setup complete"
}

# Verify installation
verify_installation() {
    log "Verifying installation..."
    
    # Check Python version
    if ! python3 --version | grep -q "3.11"; then
        warn "Python 3.11 is recommended. Current version: $(python3 --version)"
    fi
    
    # Check Node.js version
    if ! node --version | grep -q "v18"; then
        warn "Node.js 18.x is recommended. Current version: $(node --version)"
    fi
    
    # Check greenlet installation
    if ! python3 -c "import greenlet; print(f'greenlet {greenlet.__version__} installed')" &> /dev/null; then
        error "Failed to install greenlet"
        exit 1
    fi
    
    # Check Playwright installation
    if ! command -v playwright &> /dev/null; then
        error "Failed to install Playwright"
        exit 1
    fi
    
    log "Verification complete. All required components are installed."
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

# Main installation function
main() {
    log "Starting coBoarding installation for Fedora..."
    
    check_root
    check_system
    install_system_deps
    setup_python_env
    verify_installation
    
    log "\n🎉 Installation completed successfully! 🎉"
    log "\nNext steps:"
    echo -e "\n  1. Start the development server:"
    echo -e "     cd $(pwd)"
    echo -e "     source venv/bin/activate"
    echo -e "     python -m coboarding"
    echo -e "\n  2. Open your browser and navigate to: http://localhost:8501"
    
    if [[ $(id -nG "$USER" | grep -qw "docker") -eq 0 ]]; then
        warn "\n⚠️  Your user has been added to the 'docker' group."
        warn "   You need to log out and back in for this change to take effect."
    fi
    
    log "\nFor production deployment, please refer to the documentation."
}

# Run main function
main "$@"
