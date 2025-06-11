# Setup Instructions (`docs/setup.md`)

# coBoarding Setup Guide

## Prerequisites

1. **Hardware Requirements:**
   - NVIDIA GPU with 8GB+ VRAM
   - 64GB+ RAM recommended
   - 100GB+ storage space

2. **Software Requirements:**
   - Docker & Docker Compose
   - Python 3.11+
   - NVIDIA Docker support

## Installation Steps

### 1. Clone Repository
```bash
git clone https://github.com/your-org/coboarding.git
cd coboarding
```

### 2. Environment Setup
```bash
cp .env.example .env
# Edit .env with your configuration
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Download Language Models
```bash
# Download spaCy models
python -m spacy download en_core_web_sm
python -m spacy download pl_core_news_sm  
python -m spacy download de_core_news_sm

# Download Ollama models
ollama pull llava:7b
ollama pull mistral:7b
```

### 5. Start Services
```bash
docker-compose up -d
```

### 6. Verify Installation
```bash
# Check if all services are running
docker-compose ps

# Test API
curl http://localhost:8000/health

# Access UI
open http://localhost:8501
```

## LinkedIn API Setup

1. Create LinkedIn Developer Application
2. Configure OAuth redirect URI: `http://localhost:8501/callback`
3. Add Client ID and Secret to `.env`
4. Apply for LinkedIn Talent Solutions partnership

## Business Model Configuration

1. Set up payment processor (Stripe recommended)
2. Configure webhook endpoints
3. Set pricing in environment variables
4. Test payment flows in sandbox mode

## Production Deployment

1. Use `docker-compose.prod.yml`
2. Configure SSL certificates
3. Set up monitoring (Prometheus + Grafana)
4. Configure backup strategies
5. Implement proper logging

## Troubleshooting

### Common Issues:

1. **GPU not detected:**
   ```bash
   # Install NVIDIA Docker
   sudo apt install nvidia-docker2
   sudo systemctl restart docker
   ```

2. **Ollama models not loading:**
   ```bash
   # Check GPU memory
   nvidia-smi
   
   # Restart Ollama
   docker-compose