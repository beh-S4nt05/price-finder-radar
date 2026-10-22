# ICEBERG // Price Radar & Arbitrage System

Sistema full-stack de **comparação de preços multi-loja em tempo real**, **detecção estatística de promoções/bugs de preço** e **simulação de lotes de compra para revenda**, arquitetado sob princípios rigorosos de **POO, SOLID, Clean Architecture e Domain-Driven Design (DDD)**.

> **Garantia Zero Mock Data**: Em execução da aplicação, **100% das ofertas vêm de Web Scraping Real ao vivo** (`curl_cffi` TLS Chrome Impersonation, Dorks Avançados em Buscadores Web e `Playwright Headless Chromium`). Dados simulados existem exclusivamente na suíte isolada de testes unitários em `backend/tests/`.

---

## Como Clonar e Inicializar o Projeto

### Passo 1 — Clonar o Repositório

- **Opção A — Clonar Direto da sua Conta GitHub / GitLab**:
  ```bash
  git clone https://github.com/SEU_USUARIO/iceberg-price-radar.git
  cd iceberg-price-radar
  ```

- **Opção B — Via Pacote `.zip` ou Git Bundle**:
  Se baixou `iceberg-price-radar.zip` ou `iceberg-price-radar.bundle`:
  ```bash
  # Extraindo o .zip (já contém a pasta .git inicializada na branch main):
  unzip iceberg-price-radar.zip
  cd iceberg-price-radar

  # Publicando em 1 comando na sua conta via GitHub CLI (Opcional):
  gh repo create iceberg-price-radar --private --source=. --remote=origin --push
  ```

---

### Passo 2 — Inicializar e Rodar (1 Comando)

#### Windows (CMD ou PowerShell)
```bat
setup.bat
start.bat
```

#### Linux / macOS / WSL
```bash
chmod +x setup.sh start.sh
./setup.sh
./start.sh
```

#### Via Docker Compose (Opcional)
```bash
docker compose up --build
```

#### Inicialização Manual Passo a Passo (2 Terminais)
```bash
# Terminal 1 — Backend Python (FastAPI + Scrapers + SQLite)
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate  |  Linux/Mac: source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
PYTHONPATH=. uvicorn src.presentation.api:app --host 0.0.0.0 --port 8000 --reload
```

```bash
# Terminal 2 — Frontend Web (React + TypeScript + TailwindCSS v4)
cd frontend
npm install
npm run dev
```

Acesse:
- **Aplicação Web (`React + Tailwind`)**: `http://localhost:5173`
- **Documentação Interativa da API (`Swagger OpenAPI`)**: `http://localhost:8000/docs`

---

## Estrutura de Pastas (DDD + SOLID + Ports & Adapters)

```text
iceberg-price-radar/
├── setup.sh / start.sh              # Automação Linux, macOS e WSL
├── setup.bat / start.bat            # Automação Windows CMD / PowerShell
├── docker-compose.yml               # Orquestração em containers
├── .env.example                     # Modelo de variáveis de ambiente
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── data/                        # Banco SQLite persistente (Watchlist, Histórico, Alertas)
│   ├── src/
│   │   ├── domain/                  # Núcleo Puro de Negócio (Entities, Value Objects, Ports, Services)
│   │   ├── application/             # Casos de Uso (Busca Paralela, URLs, Watchlist, CSV)
│   │   ├── infrastructure/          # 8 Motores de Scraping Reais + Playwright + SQLite + WhatsApp/Webhooks
│   │   └── presentation/            # Container IoC, Schemas Pydantic v2 e FastAPI Router
│   └── tests/                       # Testes unitários isolados (pytest)
└── frontend/
    ├── Dockerfile
    ├── vite.config.ts
    └── src/
        ├── types/                   # Interfaces TypeScript do Domínio
        ├── services/                # Cliente HTTP tipado desacoplado
        ├── context/                 # Dual Cold Theme Context & Resale Lot Context
        └── components/              # Templates React Minimalistas (Grid, Tabela, URL/Dorks, Watchlist, Alertas)
```
