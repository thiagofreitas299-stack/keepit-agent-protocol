FROM python:3.11-slim

WORKDIR /app

# Instalar dependências
COPY api/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código
COPY api/main.py .

# Porta
EXPOSE 8000

CMD ["sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
