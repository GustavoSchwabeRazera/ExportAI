# ExportAI Backend

Backend FastAPI do ExportAI para recomendação de mercados internacionais por
NCM/HS6 e explicação em linguagem natural dos resultados.

## Instalar dependencias

No PowerShell, a partir da pasta `backend`:

```powershell
python -m pip install -r requirements.txt
```

## Executar em desenvolvimento

```powershell
python -m uvicorn app.main:app --reload
```

## Abrir no navegador

- API: `http://127.0.0.1:8000/`
- Health: `http://127.0.0.1:8000/health`
- Swagger: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`
- Recomendacoes: `POST /api/v1/recomendacoes`
- Explicacao com IA: `POST /api/v1/explicacao`

## IA explicativa

O endpoint `/api/v1/explicacao` recebe uma recomendacao ja calculada pelo motor
ExportAI e gera uma explicacao em linguagem natural. A IA nao recalcula o score,
nao altera o ranking e nao inventa dados fora do JSON recebido.

Por padrao, o backend tenta usar a Groq, que oferece plano Free com limites. Se
`GROQ_API_KEY` nao estiver configurada, ou se a chamada falhar/atingir limite,
o backend usa uma explicacao local deterministica para o app continuar
funcionando.

Tambem e possivel trocar para OpenAI definindo `EXPORTAI_AI_PROVIDER=openai`.

Variaveis opcionais:

```text
EXPORTAI_AI_PROVIDER=groq
EXPORTAI_AI_TIMEOUT_SECONDS=12
GROQ_API_KEY=sua_chave_groq
GROQ_MODEL=openai/gpt-oss-20b
OPENAI_API_KEY=sua_chave
OPENAI_MODEL=gpt-5
```

## Testar

```powershell
python -m pytest -q
```
