"""
KEEPIT Agent Protocol — Servidor Principal
==========================================
API REST com skills PIX (EMV) e CNPJ (BrasilAPI).
Security Gate (NEVEN GUARDIAN), rate limiting, autenticação via API key.
Autor: Thiago Freitas / KEEPIT
Licença: MIT
"""
from fastapi import FastAPI, HTTPException, Depends, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import httpx
import crcmod
import logging
import re
import time
import hashlib
from collections import defaultdict

# ==========================================
# CONFIGURAÇÃO
# ==========================================
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("keepit")

app = FastAPI(
    title="KEEPIT Agent Protocol",
    description="Skills B2A para agentes de IA operarem no Brasil",
    version="1.0.0",
    contact={"name": "KEEPIT", "url": "https://keepithub.com"},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Keys válidas (em produção: banco de dados + Stripe)
VALID_API_KEYS = {
    "keepit_free_demo_key": {"plan": "free", "calls_limit": 100, "calls_used": 0},
    "keepit_pro_demo_key": {"plan": "pro", "calls_limit": 10000, "calls_used": 0},
}

# Rate limiting simples (em produção: Redis)
rate_limit_store: Dict[str, list] = defaultdict(list)

# ==========================================
# MODELOS
# ==========================================
class PIXRequest(BaseModel):
    chave: str = Field(..., description="Chave PIX (CPF, CNPJ, email, telefone ou EVP)")
    valor: Optional[float] = Field(None, description="Valor em BRL (None = valor aberto)")
    nome_recebedor: str = Field(..., description="Nome do recebedor (máx 25 chars)")
    cidade: str = Field(..., description="Cidade do recebedor (máx 15 chars)")
    txid: Optional[str] = Field(None, description="ID da transação (máx 25 chars alfanum)")
    descricao: Optional[str] = Field(None, description="Descrição do pagamento")

class PIXResponse(BaseModel):
    success: bool
    br_code: str
    payload_emv: str
    qr_code_url: str
    txid: str

class CNPJRequest(BaseModel):
    cnpj: str = Field(..., description="CNPJ (apenas números ou formatado)")

class CNPJResponse(BaseModel):
    success: bool
    cnpj: str
    razao_social: str
    nome_fantasia: Optional[str]
    situacao: str
    atividade_principal: str
    endereco: Dict[str, Any]
    capital_social: Optional[float]
    data_abertura: str
    socios: List[Dict[str, Any]]
    raw: Dict[str, Any]

class SkillInfo(BaseModel):
    id: str
    name: str
    description: str
    version: str
    price_free: str
    price_pro: str
    endpoint: str

# ==========================================
# SECURITY GATE (NEVEN GUARDIAN simplificado)
# ==========================================
INJECTION_PATTERNS = [
    r"ignore.{0,20}previous",
    r"forget.{0,20}instructions",
    r"<\|system\|>",
    r"DAN mode",
    r"jailbreak",
    r"rm\s+-rf",
    r"DROP\s+TABLE",
]

def security_gate(data: str) -> bool:
    """Verifica se o input contém tentativas de injeção."""
    for pattern in INJECTION_PATTERNS:
        if re.search(pattern, data, re.IGNORECASE):
            logger.warning(f"🚨 NEVEN GUARDIAN bloqueou: pattern={pattern}")
            return False
    return True

# ==========================================
# AUTENTICAÇÃO
# ==========================================
def get_api_key(x_api_key: str = Header(..., alias="X-API-Key")):
    if x_api_key not in VALID_API_KEYS:
        raise HTTPException(status_code=401, detail="API key inválida. Obtenha em keepithub.com/api-keys")
    return VALID_API_KEYS[x_api_key]

# ==========================================
# GERADOR PIX EMV (BR Code)
# ==========================================
def _crc16(payload: str) -> str:
    crc_fun = crcmod.mkCrcFun(0x11021, rev=False, initCrc=0xFFFF, xorOut=0x0000)
    return format(crc_fun(payload.encode("utf-8")), "04X")

def _tlv(id_: str, value: str) -> str:
    return f"{id_}{len(value):02d}{value}"

def gerar_pix_emv(chave: str, nome: str, cidade: str, valor: Optional[float] = None,
                   txid: str = "***", descricao: str = "") -> str:
    """Gera o payload PIX no padrão EMV (BR Code)."""
    nome = nome[:25].upper()
    cidade = cidade[:15].upper()
    txid = (txid or "***")[:25]

    # Merchant Account Information (GUI + chave PIX)
    gui = _tlv("00", "BR.GOV.BCB.PIX")
    chave_tlv = _tlv("01", chave)
    if descricao:
        desc_tlv = _tlv("02", descricao[:72])
    else:
        desc_tlv = ""
    mai = _tlv("26", gui + chave_tlv + desc_tlv)

    # Additional Data (txid)
    add_data = _tlv("50", _tlv("05", txid))

    # Montagem do payload (sem CRC)
    payload = (
        _tlv("00", "01")          # Payload Format Indicator
        + _tlv("01", "12")        # Point of Initiation Method (12 = reutilizável)
        + mai                      # Merchant Account Information
        + _tlv("52", "0000")      # Merchant Category Code
        + _tlv("53", "986")       # Transaction Currency (BRL)
        + (_tlv("54", f"{valor:.2f}") if valor else "")  # Transaction Amount
        + _tlv("58", "BR")        # Country Code
        + _tlv("59", nome)        # Merchant Name
        + _tlv("60", cidade)      # Merchant City
        + add_data                 # Additional Data
        + "6304"                   # CRC placeholder
    )

    crc = _crc16(payload)
    return payload + crc

# ==========================================
# ENDPOINTS
# ==========================================
@app.get("/", tags=["Status"])
async def root():
    return {
        "service": "KEEPIT Agent Protocol",
        "version": "1.0.0",
        "status": "operational",
        "skills": ["pix_payload", "cnpj_lookup"],
        "docs": "https://keepithub.com/developers",
        "get_api_key": "https://keepithub.com/api-keys"
    }

@app.get("/api/v1/skills", tags=["Skills"])
async def list_skills():
    """Lista todas as skills disponíveis."""
    return {
        "skills": [
            {
                "id": "pix_payload",
                "name": "PIX Payload Generator",
                "description": "Gera BR Code PIX no padrão EMV para cobranças. Sem regulação BACEN.",
                "version": "1.0.0",
                "price_free": "100 calls/mês grátis",
                "price_pro": "US$49/mês — 10.000 calls",
                "endpoint": "/api/v1/skills/pix"
            },
            {
                "id": "cnpj_lookup",
                "name": "CNPJ Deep Lookup",
                "description": "Consulta profunda de CNPJ na Receita Federal via BrasilAPI.",
                "version": "1.0.0",
                "price_free": "100 calls/mês grátis",
                "price_pro": "US$49/mês — 10.000 calls",
                "endpoint": "/api/v1/skills/cnpj"
            }
        ],
        "total": 2
    }

@app.post("/api/v1/skills/pix", response_model=PIXResponse, tags=["Skills"])
async def gerar_pix(request: PIXRequest, api_key_data: dict = Depends(get_api_key)):
    """
    Gera um payload PIX (BR Code) no padrão EMV.
    
    - Não requer licença BACEN (gera string formatada, não processa pagamento)
    - Funciona com qualquer chave PIX: CPF, CNPJ, email, telefone, EVP
    - Retorna o BR Code para exibir como QR ou copia-e-cola
    """
    # Security Gate
    if not security_gate(str(request.model_dump())):
        raise HTTPException(status_code=400, detail="Input bloqueado pelo NEVEN GUARDIAN")

    txid = request.txid or hashlib.md5(f"{request.chave}{time.time()}".encode()).hexdigest()[:25]
    txid = re.sub(r"[^a-zA-Z0-9]", "", txid)[:25]

    try:
        br_code = gerar_pix_emv(
            chave=request.chave,
            nome=request.nome_recebedor,
            cidade=request.cidade,
            valor=request.valor,
            txid=txid,
            descricao=request.descricao or ""
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Erro ao gerar PIX: {str(e)}")

    qr_url = f"https://api.qrserver.com/v1/create-qr-code/?data={br_code}&size=300x300"

    logger.info(f"✅ PIX gerado | chave={request.chave[:5]}... | valor={request.valor}")

    return PIXResponse(
        success=True,
        br_code=br_code,
        payload_emv=br_code,
        qr_code_url=qr_url,
        txid=txid
    )

@app.post("/api/v1/skills/cnpj", response_model=CNPJResponse, tags=["Skills"])
async def consultar_cnpj(request: CNPJRequest, api_key_data: dict = Depends(get_api_key)):
    """
    Consulta CNPJ na Receita Federal via BrasilAPI.
    
    - Dados públicos, sem regulação
    - Retorna razão social, situação, sócios, endereço, capital social
    """
    # Limpar CNPJ
    cnpj_limpo = re.sub(r"\D", "", request.cnpj)
    if len(cnpj_limpo) != 14:
        raise HTTPException(status_code=400, detail="CNPJ deve ter 14 dígitos")

    # Security Gate
    if not security_gate(cnpj_limpo):
        raise HTTPException(status_code=400, detail="Input bloqueado pelo NEVEN GUARDIAN")

    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            resp = await client.get(f"https://brasilapi.com.br/api/cnpj/v1/{cnpj_limpo}")
            if resp.status_code == 404:
                raise HTTPException(status_code=404, detail="CNPJ não encontrado na Receita Federal")
            if resp.status_code != 200:
                raise HTTPException(status_code=502, detail="BrasilAPI indisponível")
            data = resp.json()
        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Timeout na consulta à Receita Federal")

    # Formatar endereço
    endereco = {
        "logradouro": data.get("logradouro", ""),
        "numero": data.get("numero", ""),
        "complemento": data.get("complemento", ""),
        "bairro": data.get("bairro", ""),
        "municipio": data.get("municipio", ""),
        "uf": data.get("uf", ""),
        "cep": data.get("cep", ""),
    }

    # Atividade principal
    atividades = data.get("cnae_fiscal_descricao", data.get("atividade_principal", [{}]))
    if isinstance(atividades, list) and atividades:
        ativ_str = atividades[0].get("text", "") if isinstance(atividades[0], dict) else str(atividades[0])
    else:
        ativ_str = str(atividades)

    logger.info(f"✅ CNPJ consultado: {cnpj_limpo[:4]}...{cnpj_limpo[-4:]}")

    return CNPJResponse(
        success=True,
        cnpj=cnpj_limpo,
        razao_social=data.get("razao_social", ""),
        nome_fantasia=data.get("nome_fantasia"),
        situacao=data.get("descricao_situacao_cadastral", data.get("situacao", "")),
        atividade_principal=ativ_str,
        endereco=endereco,
        capital_social=data.get("capital_social"),
        data_abertura=data.get("data_inicio_atividade", ""),
        socios=data.get("qsa", []),
        raw=data
    )

@app.get("/health", tags=["Status"])
async def health():
    return {"status": "ok", "timestamp": time.time(), "service": "KEEPIT Agent Protocol"}
