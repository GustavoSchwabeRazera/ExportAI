# ExportAI Backend

Primeira estrutura FastAPI da Sprint 7.

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

## Testar

```powershell
python -m pytest -q
```

Nesta primeira etapa existe apenas a raiz da API e o health check. O endpoint
de recomendacoes sera adicionado depois da definicao dos schemas Pydantic.
