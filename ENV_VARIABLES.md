# Environment Variables Guide for PrediBench

This guide documents all environment variables required to run the PrediBench application across its different components.

## Backend Environment Variables

### Server Configuration
- **`PORT`**: Port number for the backend server (default: `8080`)
  ```bash
  export PORT=8080
  ```

## Frontend Environment Variables

### API Configuration
- **`VITE_API_BASE_URL`**: Base URL for the backend API (default: `http://localhost:8080/api`)
  ```bash
  export VITE_API_BASE_URL=https://api.predibench.com/api
  ```

Note: Frontend uses Firebase configuration hardcoded in `src/firebase.ts` for analytics.

## Core Engine Environment Variables

### Authentication & API Keys

#### Hugging Face
- **`HF_TOKEN`**: Hugging Face authentication token for dataset access
  ```bash
  export HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
  ```

#### LLM Model APIs
- **`GEMINI_API_KEY`**: Google Gemini API key for Gemini models
  ```bash
  export GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxx
  ```

#### Search Provider APIs (Choose one or configure multiple)
- **`SERPAPI_API_KEY`**: SerpAPI key for web search
  ```bash
  export SERPAPI_API_KEY=xxxxxxxxxxxxxxxxxx
  ```

- **`SERPER_API_KEY`**: Serper.dev API key for web search
  ```bash
  export SERPER_API_KEY=xxxxxxxxxxxxxxxxxx
  ```

- **`BRIGHT_SERPER_API_KEY`**: Bright Data search API key
  ```bash
  export BRIGHT_SERPER_API_KEY=xxxxxxxxxxxxxxxxxx
  ```

#### Web Scraping APIs
- **`SCRAPFLY_API_KEY`**: ScrapFly API key for web scraping
  ```bash
  export SCRAPFLY_API_KEY=scp-live-xxxxxxxxxx
  ```

- **`SCRAPE_DO_API_KEY`**: Scrape.do API key for web scraping
  ```bash
  export SCRAPE_DO_API_KEY=xxxxxxxxxxxxxxxxxx
  ```

- **`BRIGHT_DATA_BROWSER_ENDPOINT`**: Bright Data browser CDP endpoint for scraping
  ```bash
  export BRIGHT_DATA_BROWSER_ENDPOINT=wss://brd-customer-xxxxx.dataimpulse.com
  ```

#### AI Research API
- **`PERPLEXITY_API_KEY`**: Perplexity API key for AI-powered research
  ```bash
  export PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxx
  ```

### Storage Configuration

#### Google Cloud Storage
- **`BUCKET_PREDIBENCH`**: Google Cloud Storage bucket name for data storage
  ```bash
  export BUCKET_PREDIBENCH=predibench-data
  ```

- **`BUCKET_JSON_KEY`**: JSON key for Google Cloud Storage authentication (optional if using default credentials)
  ```bash
  export BUCKET_JSON_KEY='{"type": "service_account", ...}'
  ```

- **`USE_LOCAL_STORAGE`**: Force local storage instead of bucket (default: `false`)
  ```bash
  export USE_LOCAL_STORAGE=true  # Set to use local filesystem instead of GCS
  ```

### Logging Configuration
- **`COLOREDLOGS_LOG_LEVEL`**: Log level for colored logs output (optional)
  ```bash
  export COLOREDLOGS_LOG_LEVEL=INFO  # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
  ```

## Setup Examples

### Development Environment (.env file)
```bash
# Backend
PORT=8080

# Frontend
VITE_API_BASE_URL=http://localhost:8080/api

# Core Engine
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxx
SERPER_API_KEY=xxxxxxxxxxxxxxxxxx
SCRAPFLY_API_KEY=scp-live-xxxxxxxxxx
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxx
USE_LOCAL_STORAGE=true
COLOREDLOGS_LOG_LEVEL=DEBUG
```

### Production Environment
```bash
# Backend
PORT=8080

# Frontend (set during build)
VITE_API_BASE_URL=https://api.predibench.com/api

# Core Engine
HF_TOKEN=hf_xxxxxxxxxxxxxxxxxxxxx
GEMINI_API_KEY=AIzaxxxxxxxxxxxxxxxxxx
SERPER_API_KEY=xxxxxxxxxxxxxxxxxx
BRIGHT_SERPER_API_KEY=xxxxxxxxxxxxxxxxxx
SCRAPFLY_API_KEY=scp-live-xxxxxxxxxx
BRIGHT_DATA_BROWSER_ENDPOINT=wss://brd-customer-xxxxx.dataimpulse.com
PERPLEXITY_API_KEY=pplx-xxxxxxxxxxxxxxxxxx
BUCKET_PREDIBENCH=predibench-production
BUCKET_JSON_KEY='{"type": "service_account", ...}'
COLOREDLOGS_LOG_LEVEL=INFO
```

## Loading Environment Variables

### Using dotenv (Python)
The core engine uses `python-dotenv` to load environment variables:
```python
from dotenv import load_dotenv
load_dotenv(override=True)
```

### Using Vite (Frontend)
Frontend environment variables must be prefixed with `VITE_` and are loaded automatically by Vite during build/dev.

### Docker
When using Docker, pass environment variables using:
```bash
docker run -e HF_TOKEN=xxx -e GEMINI_API_KEY=yyy predibench
```

Or use a `.env` file:
```bash
docker run --env-file .env predibench
```

## Security Notes

1. **Never commit API keys or tokens to version control**
2. Use secret management services in production (e.g., Google Secret Manager)
3. Rotate API keys regularly
4. Use least-privilege access for all service accounts
5. Store sensitive environment variables in secure locations:
   - Local: Use `.env` files (add to `.gitignore`)
   - Production: Use cloud secret managers or environment-specific configuration

## Troubleshooting

### Missing Environment Variables
If the application fails to start, check for missing required environment variables:
- Backend: Check `PORT` is set if not using default
- Frontend: Ensure `VITE_API_BASE_URL` points to correct backend
- Core: Verify at least one search API key is configured

### Storage Mode Issues
- If `BUCKET_PREDIBENCH` is not set, the system falls back to local storage
- To force local storage even with bucket configured, set `USE_LOCAL_STORAGE=true`

### API Key Validation
Test your API keys are working:
```bash
# Test Hugging Face token
curl -H "Authorization: Bearer $HF_TOKEN" https://huggingface.co/api/whoami

# Test other APIs according to their documentation
```