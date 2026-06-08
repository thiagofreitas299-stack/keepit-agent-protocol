# KEEPIT Agent Protocol

> **The missing bridge between AI agents and Brazil's economy.**

[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![API Status](https://img.shields.io/badge/API-operational-brightgreen)](https://keepithub.com/api/v1/)
[![Works with Claude](https://img.shields.io/badge/Works%20with-Claude-blueviolet)](https://anthropic.com)
[![Works with GPT](https://img.shields.io/badge/Works%20with-GPT--4-blue)](https://openai.com)

AI agents built with Claude, GPT-4, or Gemini are brilliant at reasoning — but fail miserably when trying to operate in Brazil. They can't generate PIX payments, can't look up company data from the Receita Federal, and don't understand Brazilian bureaucracy.

**KEEPIT Agent Protocol** solves this. It's a dead-simple REST API that gives your AI agent superpowers in Brazil.

---

## 🚀 Skills Available

### 1. PIX Payload Generator
Generate a valid PIX BR Code (EMV standard) for payments — in milliseconds.

```python
import requests

response = requests.post(
    "https://keepithub.com/api/v1/skills/pix",
    headers={"X-API-Key": "your_api_key"},
    json={
        "chave": "empresa@example.com",
        "valor": 149.90,
        "nome_recebedor": "Minha Empresa",
        "cidade": "São Paulo",
        "descricao": "Invoice #1234"
    }
)

br_code = response.json()["br_code"]
# Returns a valid PIX QR code string — paste into any banking app
```

**No BACEN license required.** Generating a PIX payload is string formatting — the actual payment happens in the user's banking app.

---

### 2. CNPJ Deep Lookup
Query any Brazilian company from the Receita Federal (Federal Revenue) in real-time.

```python
response = requests.post(
    "https://keepithub.com/api/v1/skills/cnpj",
    headers={"X-API-Key": "your_api_key"},
    json={"cnpj": "62.874.702/0001-51"}
)

company = response.json()
# Returns: razao_social, situacao, socios, endereco, capital_social, ...
```

---

## 🔐 Security: NEVEN GUARDIAN

Every request is filtered by **NEVEN GUARDIAN** — an infrastructure-level security proxy that:
- Blocks prompt injection attacks
- Validates input format before execution
- Logs all operations with cryptographic verification

---

## 💰 Pricing

| Plan | Calls/month | Price |
|------|------------|-------|
| Free | 100 | $0 |
| Pro | 10,000 | $49/month |
| Enterprise | Unlimited | Contact us |

**Get your API key:** [keepithub.com/api-keys](https://keepithub.com/api-keys)

---

## 📖 Quick Start

```bash
# Test the API right now (no signup required for demo)
curl -X POST https://keepithub.com/api/v1/skills/pix \
  -H "Content-Type: application/json" \
  -H "X-API-Key: keepit_free_demo_key" \
  -d '{
    "chave": "test@example.com",
    "valor": 10.00,
    "nome_recebedor": "Test User",
    "cidade": "São Paulo"
  }'
```

---

## 🤖 Use with Claude (MCP)

```json
{
  "mcpServers": {
    "keepit": {
      "url": "https://keepithub.com/mcp",
      "apiKey": "your_api_key"
    }
  }
}
```

---

## 🏗️ Architecture

```
AI Agent (Claude/GPT/Gemini)
    ↓
KEEPIT Agent Protocol API
    ↓
NEVEN GUARDIAN (Security Gate)
    ↓
Skill Engine (PIX EMV / BrasilAPI CNPJ)
    ↓
Result → Agent
```

---

## 🌐 About KEEPIT

KEEPIT is building the B2A (Business-to-Agent) infrastructure for Latin America. 
We're starting with Brazil — the 6th largest economy — because AI agents need country-specific 
capabilities to be truly useful.

**Website:** [keepithub.com](https://keepithub.com)  
**Contact:** solutions@keepithub.com  
**Twitter/X:** @keepithub  

---

## 📄 License

MIT — free to use, modify, and distribute.

Built with ❤️ in Brazil by the KEEPIT team.
