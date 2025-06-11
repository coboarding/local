# coBoarding - AI-Powered Job Application Automation

Automate your job application process with coBoarding. This tool helps you fill out job application forms automatically, including platforms like bewerbung.jobs, while maintaining compliance with international employment and data protection laws.

## Features

- **Automated Form Filling**: Intelligent detection and completion of job application forms
- **Visual Analysis**: AI-powered detection of form elements using LLaVA for better accuracy
- **Smart File Uploads**: Automatic detection and handling of file upload fields with support for multiple file types
- **Multi-language Support**: English, German, and Polish interfaces and processing
- **Smart Field Detection**: Advanced AI for accurate form field mapping
- **Document Management**: Handle resumes, cover letters, and other application materials
- **Headless Browser Automation**: Stealthy and efficient form submission
- **GDPR Compliance**: Built-in data protection and privacy controls
- **Local AI Processing**: Run models locally for enhanced privacy

## Prerequisites

1. **Hardware Requirements:**
   - CPU: x86_64 or ARM64 processor
   - RAM: 8GB minimum, 16GB+ recommended
   - Storage: 10GB+ free space (for models and data)
   - GPU: Optional but recommended for better performance

2. **Software Requirements:**
   - Python 3.11+
   - pip (Python package manager)
   - curl or wget
   - Chrome or Firefox browser
   - Systemd (for service management on Linux)

## Quick Start

### 1. Clone Repository

```bash
git clone https://github.com/your-org/coboarding.git
cd coboarding
```

### 2. Set Up Environment

```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
make install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration if needed
```

### 3. Install Ollama and Required Models

```bash
# Install Ollama and download LLaVA model
make setup-ollama

# Or run the installation script directly:
chmod +x install_ollama.sh
./install_ollama.sh

# Download additional AI models (optional)
ollama pull mistral:7b
```

### 4. Start Services

Start the Ollama service if not already running:

```bash
# Start Ollama service
make start-ollama

# Check Ollama status
make check-ollama
```

### 5. Run the Application

```bash
# For development with visual analysis enabled:
python -m coboarding.automation.job_applicator --url YOUR_JOB_POSTING_URL --visual

# Or use the Makefile target:
make apply-job-visual URL=YOUR_JOB_POSTING_URL

# For standard mode (without visual analysis):
make apply-job URL=YOUR_JOB_POSTING_URL
```

## File Upload Support

### Supported File Types

- **Resume/CV**: `resume.pdf`, `cv.pdf`, `lebenslauf.pdf`
- **Cover Letter**: `cover_letter.pdf`, `anschreiben.pdf`, `motivation.pdf`
- **Certificates**: `certificates.pdf`, `zeugnisse.pdf`
- **Photo**: `photo.jpg`, `bild.jpg`, `profile.jpg`

### Visual Analysis Features

The system uses LLaVA (a vision-language model) to:
- Detect file upload buttons and areas visually
- Handle custom-styled upload components
- Provide fallback mechanisms when standard detection fails
- Generate debug screenshots for troubleshooting

## Managing Ollama Service

```bash
# Start the Ollama service
make start-ollama

# Stop the Ollama service
make stop-ollama

# Check if Ollama is running
make check-ollama

# Install/update Ollama and LLaVA model
make setup-ollama
```

## Troubleshooting

### Ollama Service Issues

If you encounter issues with the Ollama service:

1. Check if the service is running:
   ```bash
   systemctl --user status ollama
   ```

2. View service logs:
   ```bash
   journalctl --user -u ollama -f
   ```

3. Verify Ollama API is accessible:
   ```bash
   curl http://localhost:11434/api/tags
   ```

### Visual Analysis Not Working

If visual analysis fails:
1. Ensure Ollama service is running
2. Verify the LLaVA model is installed:
   ```bash
   ollama list
   ```
3. Check for error messages in the application logs
4. Make sure you're using the `--visual` flag when running the application

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
