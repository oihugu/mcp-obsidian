# Plano de Deployment - MCP Obsidian Server via Cloudflare Tunnel

**Data:** 2025-10-25
**Objetivo:** Deployar o servidor MCP Obsidian na rede local e expor via Cloudflare Tunnel

---

## 📊 Visão Geral

### Arquitetura Atual vs. Proposta

**Atual:**
```
Cliente (Claude Desktop) ←→ MCP Server (stdio) ←→ Obsidian API (HTTP)
```

**Proposta:**
```
Cliente Web/API ←→ Cloudflare Tunnel ←→ HTTP Server ←→ MCP Server ←→ Obsidian API
                    (Internet)          (Rede Local)
```

---

## 🏗️ Arquitetura de Deployment

### Opção 1: HTTP REST API (Recomendado)

**Componentes:**
```
┌─────────────────────────────────────────────────────────────┐
│                     Internet (Cloudflare)                    │
├─────────────────────────────────────────────────────────────┤
│                    Cloudflare Tunnel                         │
│                  (cloudflared daemon)                        │
├─────────────────────────────────────────────────────────────┤
│              Rede Local (192.168.x.x)                        │
│  ┌───────────────────────────────────────────────────┐     │
│  │  FastAPI/Flask HTTP Server (Port 8000)            │     │
│  │  ├─ Authentication (JWT/API Key)                  │     │
│  │  ├─ Rate Limiting                                 │     │
│  │  ├─ Logging & Monitoring                          │     │
│  │  └─ MCP Tools Handler                             │     │
│  └───────────────────────────────────────────────────┘     │
│                        ↓                                     │
│  ┌───────────────────────────────────────────────────┐     │
│  │  MCP Obsidian Core                                │     │
│  │  ├─ 31 Tools (Discovery, CRUD, Semantic)          │     │
│  │  ├─ Embeddings Manager (FAISS + Cache)            │     │
│  │  └─ Configuration Manager                         │     │
│  └───────────────────────────────────────────────────┘     │
│                        ↓                                     │
│  ┌───────────────────────────────────────────────────┐     │
│  │  Obsidian Local REST API                          │     │
│  │  (secondbrain.oihugudev.com.br:80)               │     │
│  └───────────────────────────────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

**Vantagens:**
- ✅ Fácil integração com Cloudflare Tunnel
- ✅ Suporta autenticação e rate limiting
- ✅ Logs centralizados
- ✅ Pode servir interface web opcional
- ✅ Escalável

**Stack Tecnológico:**
- **Framework**: FastAPI (Python)
- **ASGI Server**: Uvicorn
- **Autenticação**: JWT ou API Keys
- **Containerização**: Docker
- **Proxy**: Cloudflare Tunnel
- **Monitoramento**: Prometheus + Grafana (opcional)

---

### Opção 2: WebSocket Server

**Componentes:**
```
Cliente ←→ Cloudflare Tunnel ←→ WebSocket Server ←→ MCP Core
```

**Vantagens:**
- ✅ Comunicação bidirecional
- ✅ Real-time updates
- ✅ Melhor para operações longas

**Desvantagens:**
- ⚠️ Mais complexo de implementar
- ⚠️ Requer gerenciamento de conexões

---

## 🚀 Plano de Implementação

### Fase 1: Criar HTTP API Wrapper

#### 1.1 Estrutura de Diretórios

```
mcp-obsidian/
├── src/
│   ├── mcp_obsidian/           # Core MCP (já existe)
│   └── api/                    # Novo: HTTP API wrapper
│       ├── __init__.py
│       ├── server.py           # FastAPI app
│       ├── auth.py             # Autenticação
│       ├── middleware.py       # Rate limiting, CORS
│       ├── models.py           # Pydantic models
│       └── routers/
│           ├── tools.py        # Endpoints para tools
│           ├── semantic.py     # Endpoints semânticos
│           ├── crud.py         # Endpoints CRUD
│           └── admin.py        # Admin endpoints
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── .env.example
├── cloudflare/
│   ├── tunnel-config.yml
│   └── setup.sh
└── deployment/
    ├── systemd/
    │   └── mcp-obsidian.service
    └── nginx/
        └── nginx.conf (opcional)
```

#### 1.2 Implementar FastAPI Server

**src/api/server.py:**
```python
from fastapi import FastAPI, Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
import uvicorn

from ..mcp_obsidian import tools
from .auth import verify_token
from .middleware import rate_limit_middleware
from .models import ToolRequest, ToolResponse

app = FastAPI(
    title="MCP Obsidian API",
    version="0.3.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configurar no production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()

# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": "0.3.0"}

# Tool execution endpoint
@app.post("/api/v1/tools/{tool_name}", response_model=ToolResponse)
async def execute_tool(
    tool_name: str,
    request: ToolRequest,
    credentials: HTTPAuthorizationCredentials = Security(security)
):
    # Verify authentication
    await verify_token(credentials.credentials)

    # Get tool handler
    handler = tools.get_tool_handler(tool_name)
    if not handler:
        raise HTTPException(status_code=404, detail=f"Tool not found: {tool_name}")

    # Execute tool
    try:
        result = handler.run_tool(request.args)
        return ToolResponse(
            success=True,
            tool_name=tool_name,
            result=result[0].text if result else None
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# List available tools
@app.get("/api/v1/tools")
async def list_tools(credentials: HTTPAuthorizationCredentials = Security(security)):
    await verify_token(credentials.credentials)

    return {
        "tools": [
            {
                "name": th.name,
                "description": th.get_tool_description().description
            }
            for th in tools.tool_handlers.values()
        ]
    }

if __name__ == "__main__":
    uvicorn.run(
        "src.api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
```

**src/api/auth.py:**
```python
import os
import jwt
from fastapi import HTTPException, status
from datetime import datetime, timedelta

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "your-secret-key-change-in-production")
ALGORITHM = "HS256"
API_KEYS = os.getenv("API_KEYS", "").split(",")

async def verify_token(token: str):
    """Verify JWT token or API key."""

    # Check if it's an API key
    if token in API_KEYS:
        return True

    # Verify JWT
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp and datetime.fromtimestamp(exp) < datetime.now():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired"
            )
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )

def create_access_token(data: dict, expires_delta: timedelta = None):
    """Create JWT access token."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(hours=24)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt
```

**src/api/models.py:**
```python
from pydantic import BaseModel
from typing import Any, Dict, Optional

class ToolRequest(BaseModel):
    args: Dict[str, Any] = {}

class ToolResponse(BaseModel):
    success: bool
    tool_name: str
    result: Optional[str] = None
    error: Optional[str] = None
```

---

### Fase 2: Dockerização

#### 2.1 Dockerfile

**docker/Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .
COPY setup.py .

# Install Python dependencies
RUN pip install --no-cache-dir -e .
RUN pip install --no-cache-dir fastapi uvicorn[standard] pyjwt python-multipart

# Copy application
COPY src/ ./src/
COPY .env.example .env

# Create cache directory
RUN mkdir -p .mcp-obsidian

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:8000/health')"

# Run server
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### 2.2 Docker Compose

**docker/docker-compose.yml:**
```yaml
version: '3.8'

services:
  mcp-obsidian:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: mcp-obsidian-server
    restart: unless-stopped
    ports:
      - "8000:8000"
    environment:
      - OBSIDIAN_API_KEY=${OBSIDIAN_API_KEY}
      - OBSIDIAN_HOST=${OBSIDIAN_HOST}
      - OBSIDIAN_PORT=${OBSIDIAN_PORT}
      - OBSIDIAN_PROTOCOL=${OBSIDIAN_PROTOCOL}
      - JWT_SECRET_KEY=${JWT_SECRET_KEY}
      - API_KEYS=${API_KEYS}
    volumes:
      - ../src:/app/src
      - embeddings-cache:/app/.mcp-obsidian
      - logs:/app/logs
    networks:
      - mcp-network
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  # Optional: Prometheus for monitoring
  prometheus:
    image: prom/prometheus:latest
    container_name: mcp-prometheus
    restart: unless-stopped
    ports:
      - "9090:9090"
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus-data:/prometheus
    networks:
      - mcp-network
    profiles:
      - monitoring

  # Optional: Grafana for dashboards
  grafana:
    image: grafana/grafana:latest
    container_name: mcp-grafana
    restart: unless-stopped
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana
    networks:
      - mcp-network
    profiles:
      - monitoring

volumes:
  embeddings-cache:
  logs:
  prometheus-data:
  grafana-data:

networks:
  mcp-network:
    driver: bridge
```

#### 2.3 Environment Variables

**docker/.env.example:**
```bash
# Obsidian API Configuration
OBSIDIAN_API_KEY=07452926311ed660b8a3d309a2581979dbe404a393375635c20873e94aadb870
OBSIDIAN_HOST=secondbrain.oihugudev.com.br
OBSIDIAN_PORT=80
OBSIDIAN_PROTOCOL=http

# Authentication
JWT_SECRET_KEY=your-super-secret-jwt-key-change-this
API_KEYS=key1-abc123,key2-def456,key3-ghi789

# Server Configuration
SERVER_HOST=0.0.0.0
SERVER_PORT=8000
LOG_LEVEL=INFO

# Rate Limiting
RATE_LIMIT_PER_MINUTE=60
```

---

### Fase 3: Cloudflare Tunnel Setup

#### 3.1 Instalação do Cloudflared

**Opção A: Instalação Nativa (Linux)**
```bash
# Download cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb

# Install
sudo dpkg -i cloudflared-linux-amd64.deb

# Authenticate
cloudflared tunnel login
```

**Opção B: Docker Container**
```yaml
# Adicionar ao docker-compose.yml

  cloudflared:
    image: cloudflare/cloudflared:latest
    container_name: mcp-cloudflared
    restart: unless-stopped
    command: tunnel --config /etc/cloudflared/config.yml run
    volumes:
      - ./cloudflare/config.yml:/etc/cloudflared/config.yml
      - ./cloudflare/credentials.json:/etc/cloudflared/credentials.json
    networks:
      - mcp-network
    depends_on:
      - mcp-obsidian
```

#### 3.2 Criar Tunnel

```bash
# Create tunnel
cloudflared tunnel create mcp-obsidian

# Isso irá gerar:
# - Tunnel UUID
# - credentials.json (guardar com segurança!)

# Exemplo de output:
# Tunnel credentials written to: /home/user/.cloudflared/<UUID>.json
# Created tunnel mcp-obsidian with id <UUID>
```

#### 3.3 Configurar Tunnel

**cloudflare/tunnel-config.yml:**
```yaml
tunnel: <YOUR-TUNNEL-UUID>
credentials-file: /etc/cloudflared/credentials.json

ingress:
  # MCP Obsidian API
  - hostname: mcp-obsidian.yourdomain.com
    service: http://mcp-obsidian:8000
    originRequest:
      connectTimeout: 30s
      noTLSVerify: false

  # Health check endpoint
  - hostname: mcp-obsidian.yourdomain.com
    path: /health
    service: http://mcp-obsidian:8000

  # Catch-all (404)
  - service: http_status:404
```

#### 3.4 Configurar DNS

```bash
# Route DNS to tunnel
cloudflared tunnel route dns mcp-obsidian mcp-obsidian.yourdomain.com

# Verificar no Cloudflare Dashboard:
# DNS > Records > Tipo CNAME > mcp-obsidian.yourdomain.com → UUID.cfargotunnel.com
```

#### 3.5 Iniciar Tunnel

**Opção A: Systemd Service**

**deployment/systemd/cloudflared.service:**
```ini
[Unit]
Description=Cloudflare Tunnel for MCP Obsidian
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>/mcp-obsidian
ExecStart=/usr/local/bin/cloudflared tunnel --config /path/to/tunnel-config.yml run mcp-obsidian
Restart=on-failure
RestartSec=10s

[Install]
WantedBy=multi-user.target
```

```bash
# Enable and start
sudo systemctl enable cloudflared
sudo systemctl start cloudflared
sudo systemctl status cloudflared
```

**Opção B: Docker Compose** (já incluído acima)

```bash
docker-compose up -d cloudflared
```

---

### Fase 4: Segurança e Hardening

#### 4.1 Autenticação Multi-Layer

**Camada 1: Cloudflare Access (Recomendado)**
```yaml
# Configurar no Cloudflare Dashboard:
# Access > Applications > Add Application

Application Settings:
  - Name: MCP Obsidian API
  - Domain: mcp-obsidian.yourdomain.com
  - Session Duration: 24 hours

Access Policies:
  - Name: Authorized Users
  - Action: Allow
  - Include: Email addresses ending in @yourdomain.com
  - Or: Specific email addresses

Service Authentication:
  - Service Token for API access
```

**Camada 2: JWT/API Keys** (já implementado no FastAPI)

**Camada 3: Rate Limiting**

**src/api/middleware.py:**
```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# Add to FastAPI app:
# app.state.limiter = limiter
# app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/api/v1/tools/{tool_name}")
@limiter.limit("60/minute")  # 60 requests per minute
async def execute_tool(...):
    ...
```

#### 4.2 Firewall Rules

```bash
# UFW (Ubuntu)
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 8000/tcp  # MCP Server (apenas local)
sudo ufw enable

# Apenas permitir acesso via Cloudflare IPs
# (opcional, para extra security)
```

#### 4.3 HTTPS/TLS

O Cloudflare Tunnel já provê HTTPS automaticamente:
- Cloudflare ←→ Tunnel: TLS criptografado
- Tunnel ←→ Server: Pode ser HTTP local (já está na rede privada)

**Opcional: TLS local também**
- Configurar certificados auto-assinados
- Ou usar Let's Encrypt com certbot

#### 4.4 Logging e Auditoria

**src/api/server.py (adicionar middleware):**
```python
import logging
from fastapi import Request
import time

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/mcp-obsidian.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger("mcp-api")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()

    response = await call_next(request)

    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} "
        f"- Status: {response.status_code} "
        f"- Duration: {process_time:.2f}s "
        f"- Client: {request.client.host}"
    )

    return response
```

---

## 📋 Checklist de Deployment

### Preparação

- [ ] Instalar Docker e Docker Compose
- [ ] Instalar cloudflared
- [ ] Ter domínio configurado no Cloudflare
- [ ] Gerar credenciais seguras (JWT_SECRET_KEY, API_KEYS)

### Build e Teste Local

- [ ] Implementar FastAPI wrapper
- [ ] Criar Dockerfile
- [ ] Criar docker-compose.yml
- [ ] Testar build local: `docker-compose build`
- [ ] Testar servidor local: `docker-compose up`
- [ ] Verificar health check: `curl http://localhost:8000/health`
- [ ] Testar endpoints com Postman/curl

### Cloudflare Tunnel

- [ ] Autenticar cloudflared: `cloudflared tunnel login`
- [ ] Criar tunnel: `cloudflared tunnel create mcp-obsidian`
- [ ] Salvar credentials.json em local seguro
- [ ] Criar tunnel-config.yml
- [ ] Configurar DNS: `cloudflared tunnel route dns ...`
- [ ] Testar tunnel localmente
- [ ] Configurar serviço systemd ou Docker

### Segurança

- [ ] Configurar Cloudflare Access (opcional mas recomendado)
- [ ] Gerar API Keys fortes
- [ ] Configurar JWT_SECRET_KEY
- [ ] Habilitar rate limiting
- [ ] Configurar CORS apropriadamente
- [ ] Revisar logs

### Monitoramento

- [ ] Configurar logs centralizados
- [ ] Setup Prometheus (opcional)
- [ ] Setup Grafana dashboards (opcional)
- [ ] Configurar alertas
- [ ] Testar health checks

### Go Live

- [ ] Deploy container em produção
- [ ] Iniciar cloudflared tunnel
- [ ] Verificar acesso via URL pública
- [ ] Testar todos os endpoints
- [ ] Verificar performance
- [ ] Monitorar logs por 24h

---

## 🔧 Comandos Úteis

### Docker

```bash
# Build
docker-compose build

# Start
docker-compose up -d

# Stop
docker-compose down

# Logs
docker-compose logs -f mcp-obsidian

# Restart
docker-compose restart mcp-obsidian

# Shell into container
docker-compose exec mcp-obsidian bash

# With monitoring
docker-compose --profile monitoring up -d
```

### Cloudflare Tunnel

```bash
# List tunnels
cloudflared tunnel list

# Get tunnel info
cloudflared tunnel info mcp-obsidian

# Test configuration
cloudflared tunnel --config tunnel-config.yml run mcp-obsidian

# Check logs
journalctl -u cloudflared -f
```

### Testing

```bash
# Health check
curl https://mcp-obsidian.yourdomain.com/health

# List tools (com autenticação)
curl -H "Authorization: Bearer YOUR-API-KEY" \
  https://mcp-obsidian.yourdomain.com/api/v1/tools

# Execute tool
curl -X POST \
  -H "Authorization: Bearer YOUR-API-KEY" \
  -H "Content-Type: application/json" \
  -d '{"args": {"query": "test search"}}' \
  https://mcp-obsidian.yourdomain.com/api/v1/tools/obsidian_semantic_search
```

---

## 📊 Estimativa de Recursos

### Servidor

**Mínimo:**
- CPU: 2 cores
- RAM: 4GB
- Disco: 20GB (10GB para modelo de embeddings + cache)
- Rede: 100Mbps

**Recomendado:**
- CPU: 4 cores
- RAM: 8GB
- Disco: 50GB SSD
- Rede: 1Gbps

### Custos

**Cloudflare:**
- Tunnel: Gratuito
- Cloudflare Access: $3/usuário/mês (opcional)
- DNS: Gratuito

**Servidor (exemplos):**
- VPS Local: ~R$50-100/mês
- Raspberry Pi 4 (8GB): ~R$800 (uma vez) + energia
- NUC/Mini PC: ~R$1500-3000 (uma vez) + energia

---

## 🚧 Próximos Passos

### Curto Prazo
1. Implementar FastAPI wrapper
2. Criar Dockerfile e docker-compose
3. Testar localmente
4. Setup Cloudflare Tunnel
5. Deploy inicial

### Médio Prazo
1. Adicionar interface web (React/Vue)
2. Implementar webhook para auto-rebuild de embeddings
3. Adicionar métricas e dashboards
4. Otimizar performance

### Longo Prazo
1. Multi-tenant support
2. Backup automático de cache
3. High availability setup
4. Escalabilidade horizontal

---

**Preparado por:** Claude Code
**Data:** 2025-10-25
**Status:** Pronto para implementação
