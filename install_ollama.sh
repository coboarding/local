#!/bin/bash

# Install Ollama and ensure LLaVA model is available
set -e

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to install Ollama on Debian/Ubuntu
install_ollama_deb() {
    echo "Installing Ollama on Debian/Ubuntu..."
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Add current user to ollama group
    sudo usermod -aG ollama $USER
    
    # Start and enable the service
    sudo systemctl enable ollama
    sudo systemctl start ollama
    
    # Wait for the service to start
    sleep 5
}

# Function to install Ollama on Fedora
install_ollama_fedora() {
    echo "Installing Ollama on Fedora..."
    
    # Install required dependencies
    sudo dnf -y install lzma libstdc++
    
    # Download and install Ollama
    curl -fsSL https://ollama.com/install.sh | sh
    
    # Add current user to ollama group
    sudo usermod -aG ollama $USER
    
    # Start and enable the service
    sudo systemctl enable ollama
    sudo systemctl start ollama
    
    # Wait for the service to start
    sleep 5
}

# Function to ensure LLaVA model is available
ensure_llava_model() {
    echo "Checking for LLaVA model..."
    
    # Check if ollama command is available
    if ! command_exists ollama; then
        echo "Error: Ollama is not installed or not in PATH"
        exit 1
    fi
    
    # Check if LLaVA model is already installed
    if ollama list | grep -q "llava"; then
        echo "LLaVA model is already installed."
    else
        echo "Pulling LLaVA model... (this may take a while)"
        ollama pull llava:7b
    fi
    
    # Verify the model is working
    echo -e "\nVerifying LLaVA model..."
    ollama run llava:7b --version
}

# Main script
main() {
    # Check if running as root
    if [ "$EUID" -eq 0 ]; then
        echo "Error: This script should not be run as root"
        exit 1
    fi
    
    # Detect Linux distribution
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        case $ID in
            debian|ubuntu|linuxmint)
                if ! command_exists ollama; then
                    install_ollama_deb
                fi
                ;;
            fedora|rhel|centos)
                if ! command_exists ollama; then
                    install_ollama_fedora
                fi
                ;;
            *)
                echo "Unsupported distribution: $ID"
                echo "Please install Ollama manually from https://ollama.com"
                exit 1
                ;;
        esac
        
        # Ensure LLaVA model is available
        ensure_llava_model
        
        echo -e "\nOllama and LLaVA model are ready to use!"
        echo "You may need to log out and log back in for group changes to take effect."
    else
        echo "Error: Could not detect Linux distribution"
        exit 1
    fi
}

main "$@"
