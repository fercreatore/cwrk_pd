# FastAPI Deployment Guide — Calzalindo Freelance

**Target Server:** 192.168.2.112 (DATASVRW)
**App Path:** `C:\calzalindo_freelance`
**Python:** 3.14 @ `C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe`
**Port:** 8001

---

## Files Overview

| File | Purpose |
|------|---------|
| `start_freelance.bat` | Manual startup script (for debugging/development) |
| `install_service.bat` | Install as Windows service with NSSM (production) |
| `deploy_112.sh` | Deploy from Mac to Windows server via SMB |
| `requirements.txt` | Python dependencies |
| `DEPLOYMENT.md` | This guide |

---

## Quick Start — Deploy from Mac

### 1. Deploy Code to Server
```bash
cd /path/to/cowork_pedidos/_freelance/src
./deploy_112.sh
```

Options:
```bash
./deploy_112.sh --dryrun    # Preview what will be copied
./deploy_112.sh --force     # Skip confirmation
```

**Requires:**
- VPN L2TP connected to 192.168.2.112
- rsync installed on Mac
- SMB mounted or credentials ready

---

## Option A — Manual Startup (Development)

### On Windows Server (192.168.2.112):

1. Open Command Prompt (CMD)
2. Navigate to app:
   ```batch
   cd C:\calzalindo_freelance
   ```
3. Run startup script:
   ```batch
   start_freelance.bat
   ```
4. Verify at: `http://localhost:8001`
5. Press Ctrl+C to stop

---

## Option B — Windows Service (Production)

### Prerequisites
- Administrator access on server
- NSSM (Non-Sucking Service Manager) installed

### Install NSSM
1. Download from: https://nssm.cc/download
2. Extract `nssm-2.24-101-g897c7ee\win64\nssm.exe` to `C:\nssm\`
3. Verify:
   ```batch
   C:\nssm\nssm.exe --version
   ```

### Install Service
1. On Windows Server, open Command Prompt **as Administrator**
2. Navigate to app:
   ```batch
   cd C:\calzalindo_freelance
   ```
3. Run install script:
   ```batch
   install_service.bat
   ```
4. Service `CalzalindoFreelance` will be created and auto-started

### Service Management

**Start:**
```batch
net start CalzalindoFreelance
```

**Stop:**
```batch
net stop CalzalindoFreelance
```

**View status:**
```batch
nssm status CalzalindoFreelance
```

**View error log:**
```batch
nssm get CalzalindoFreelance AppStderr
```

**Uninstall:**
```batch
nssm remove CalzalindoFreelance confirm
```

---

## Dependencies

All Python packages listed in `requirements.txt`:
- **fastapi** — Web framework
- **uvicorn** — ASGI server
- **pyodbc** — SQL Server driver
- **pymysql** — MySQL driver
- **pydantic** — Data validation
- **pydantic-settings** — Configuration management
- **python-dateutil** — Date utilities
- **jinja2** — Templates
- **python-multipart** — Form data handling
- **pillow** — Image processing

Install on server:
```batch
C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe -m pip install -r requirements.txt
```

---

## Verification

### Quick test:
```bash
# From Mac
ssh administrador@192.168.2.112
curl http://localhost:8001/docs
```

Or navigate to: `http://192.168.2.112:8001/docs`

### Check running process:
```batch
netstat -ano | findstr 8001
```

### View logs (if service):
```batch
tail -f C:\calzalindo_freelance\logs\stderr.log
```

---

## Troubleshooting

### Port 8001 already in use
```batch
netstat -ano | findstr 8001
taskkill /PID <PID> /F
```

### Module not found (Python path issue)
- Verify Python 3.14 path in scripts
- Check `requirements.txt` is installed
- Use full Python path: `C:\Users\fer\AppData\Local\Programs\Python\Python314\python.exe`

### NSSM service fails to start
1. Check app directory exists: `C:\calzalindo_freelance`
2. Verify Python path is correct
3. Check logs: `nssm get CalzalindoFreelance AppStderr`
4. Try manual `start_freelance.bat` first to see errors

### SMB mount fails (from Mac)
```bash
# Verify VPN is connected
ping 192.168.2.112

# Manual mount if deploy fails
sudo mount_smbfs '//administrador:cagr$2011@192.168.2.112/c$/calzalindo_freelance' /Volumes/cowork_112
```

---

## Environment Variables

If needed, set environment variables in `install_service.bat`:

```batch
"%NSSM_PATH%" set "%SERVICE_NAME%" AppEnvironmentExtra PYTHONUNBUFFERED=1
"%NSSM_PATH%" set "%SERVICE_NAME%" AppEnvironmentExtra DEBUG=0
```

---

## Auto-restart on Failure

The NSSM service is configured to:
- Restart on failure after 5 seconds
- Throttle restart (max once every 1.5s if continuously failing)
- Log output to `C:\calzalindo_freelance\logs\`

---

## Contact

Server admin: 192.168.2.112 (DATASVRW)
App owner: Fernando Calaianov (Cowork)
