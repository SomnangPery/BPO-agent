# Deployment Guide for IC Agent

## Pre-Deployment Checklist

- [ ] Environment variables configured via `.env` file
- [ ] API keys and tokens are secure and not committed to version control
- [ ] `FLASK_ENV=production` is set in production
- [ ] `WEB_SECRET_KEY` is set to a secure random value
- [ ] `IC_STAFF_PASSWORD` is set to a secure password
- [ ] All dependencies installed: `pip install -r requirements.txt`
- [ ] Database initialized: `python -c "from ic_agent.database import init_db; init_db()"`
- [ ] Google credentials configured if using Google Drive integration
- [ ] Telegram token configured if using Telegram bot (optional)

## Environment Setup

### 1. Create `.env` file from template

```bash
cp .env.example .env
```

### 2. Configure required variables in `.env`

```env
FLASK_ENV=production
PORT=5000
FLASK_HOST=0.0.0.0

# Required for production
ANTHROPIC_API_KEY=your-api-key
WEB_SECRET_KEY=generate-with-: python -c "import secrets; print(secrets.token_hex(32))"
IC_STAFF_PASSWORD=your-secure-password
TELEGRAM_BOT_TOKEN=your-bot-token

# Google Drive integration
GOOGLE_DRIVE_FOLDER_ID=your-folder-id
# Option A: Path to file (not recommended for cloud)
GOOGLE_CREDENTIALS_PATH=credentials.json
# Option B: JSON string (recommended for Railway/Heroku)
GOOGLE_CREDENTIALS_JSON='{"type": "service_account", ...}'
```

### 3. Railway Deployment

This project includes a `Procfile` for Railway. It will automatically start two processes:
1. `web`: The Flask web interface.
2. `bot`: The Telegram bot (Long Polling).

Ensure you have set `TELEGRAM_BOT_TOKEN` in your Railway variables for the bot to work.

### 4. Generate a secure `WEB_SECRET_KEY`

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Copy the output and paste into `.env`:
```env
WEB_SECRET_KEY=<generated-value>
```

### 4. Set IC_STAFF_PASSWORD

Use a strong password (min 12 chars, mix of upper/lower/numbers/symbols):
```env
IC_STAFF_PASSWORD=<your-secure-password>
```

## Installation & Running

### Option 1: Local Development

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Run in development mode
FLASK_ENV=development python main.py
```

### Option 2: Production Deployment

```bash
# Set production environment
export FLASK_ENV=production
export PORT=8000

# Install dependencies
pip install -r requirements.txt

# Run with production server (using Gunicorn)
pip install gunicorn
gunicorn --workers 4 --bind 0.0.0.0:8000 "ic_agent.server:create_app()"
```

### Option 3: Docker (Recommended for Production)

Create a `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

COPY . .

RUN python -c "from ic_agent.database import init_db; init_db()"

EXPOSE 8000
ENV FLASK_ENV=production

CMD ["gunicorn", "--workers", "4", "--bind", "0.0.0.0:8000", "ic_agent.server:create_app()"]
```

Build and run:
```bash
docker build -t ic-agent .
docker run -d \
  --name ic-agent \
  -p 8000:8000 \
  -e ANTHROPIC_API_KEY="your-key" \
  -e WEB_SECRET_KEY="your-secret" \
  -e IC_STAFF_PASSWORD="your-password" \
  -v $(pwd)/.env:/app/.env \
  ic-agent
```

## Security Best Practices

### 🔒 Never commit sensitive data

- `.env` should be in `.gitignore` (already configured)
- `credentials.json` should be in `.gitignore` (already configured)
- Review commits before pushing: `git diff --cached`

### 🔐 API Keys & Secrets

- Rotate `WEB_SECRET_KEY` regularly
- Use environment variables or secret management services (AWS Secrets Manager, Azure Key Vault, etc.)
- Never share or expose tokens in logs

### 🛡️ HTTPS in Production

- Always use HTTPS in production
- Configure your reverse proxy (nginx, Apache) to handle SSL/TLS
- Set `SESSION_COOKIE_SECURE=True` (automatically set in production mode)

### 📋 Monitoring & Logging

- Monitor application logs for errors
- Set up alerts for critical errors
- Keep API quotas in check (Google Drive, Anthropic)
- Monitor database size periodically

## Troubleshooting

### Missing ANTHROPIC_API_KEY

```
ValueError: ANTHROPIC_API_KEY is required in production
```

**Solution:** Add to `.env`:
```env
ANTHROPIC_API_KEY=your-actual-api-key
```

### Missing WEB_SECRET_KEY

```
ValueError: WEB_SECRET_KEY must be set in production
```

**Solution:** Generate and add to `.env`:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
# Copy output to:
WEB_SECRET_KEY=<generated-value>
```

### Port Already in Use

```
Address already in use
```

**Solution:** Change port in `.env`:
```env
PORT=8001  # or any available port
```

Or kill the process using the port:
```bash
# Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# Linux/macOS:
lsof -i :5000
kill -9 <PID>
```

## Health Check

Once deployed, verify the application is running:

```bash
curl http://localhost:5000/health
# Should return: {"status":"ok"}
```

## Maintenance

### Database Backup

The SQLite database is stored in `ic_agent.db`. Regular backups are recommended:

```bash
cp ic_agent.db ic_agent.db.backup.$(date +%Y%m%d-%H%M%S)
```

### Updating Dependencies

```bash
pip install --upgrade -r requirements.txt
```

### Viewing Logs

```bash
# If using Gunicorn:
journalctl -u ic-agent -f

# Or check Flask logs in the container/process output
```

## Support

For issues or questions, refer to the main [README.md](README.md) or check logs for detailed error messages.
