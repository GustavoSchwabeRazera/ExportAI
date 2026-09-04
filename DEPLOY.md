# Deploy do ExportAI Backend

## Validacao local sem Docker

```powershell
python -m pytest -q
python start.py
```

Abra:

- `http://127.0.0.1:8000/health`
- `http://127.0.0.1:8000/docs`

## Validacao com Docker

Na pasta `backend`:

```powershell
docker build -t exportai-api:0.2.0 .
docker run --rm -p 8000:8000 --name exportai-api exportai-api:0.2.0
```

Em outro terminal:

```powershell
docker ps
docker inspect --format='{{json .State.Health}}' exportai-api
```

## Docker Compose

```powershell
Copy-Item .env.production.example .env
# Edite EXPORTAI_CORS_ORIGINS no arquivo .env
docker compose up --build
```

Para encerrar:

```powershell
docker compose down
```

## Variaveis de ambiente

- `PORT`: porta HTTP, padrao 8000.
- `EXPORTAI_DATA_DIR`: pasta das bases, padrao `/code/data` no container.
- `EXPORTAI_CORS_ORIGINS`: origens permitidas separadas por virgula.

## Observacoes

- Nao use `--reload` em producao.
- A imagem inclui as bases Parquet necessarias para o MVP.
- Antes do deploy remoto, configure a origem HTTPS real do frontend.
- O endpoint de saude e `/health`.
