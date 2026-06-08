# KEEPIT Agent Protocol

Skills B2A para agentes de IA operarem no Brasil.

## Skills Disponíveis
- **PIX Payload** — Gera BR Code PIX (EMV) sem licença BACEN
- **CNPJ Lookup** — Consulta Receita Federal via BrasilAPI

## Deploy Local
```bash
cd api
pip install -r requirements.txt
uvicorn main:app --reload
```

## API Docs
http://localhost:8000/docs

## Produção
https://keepithub.com/developers
