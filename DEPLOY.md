# Deploy do ExportAI Backend

## Associação de produtos com IA

A rota existente `GET /api/v1/produtos?q=...` usa a busca local primeiro.
Quando não há uma correspondência local forte, pode consultar o Groq para
traduzir nomes populares em termos técnicos e selecionar candidatos reais.
Utiliza `GROQ_API_KEY` e `GROQ_MODEL` já configurados no backend; a chave não
deve ser colocada no Lovable. Para desativar, defina
`EXPORTAI_BUSCA_IA_ENABLED=false`. O timeout por chamada é configurado por
`EXPORTAI_BUSCA_IA_TIMEOUT_SECONDS` (padrão: 4 segundos); uma busca pode fazer
duas chamadas. Resultados são armazenados em cache por aproximadamente uma
hora, limitado a 256 consultas por processo. Falhas mantêm a busca local e
pausam o provedor por 30 segundos. Apenas uma consulta de IA ocorre por vez
em cada processo, e as demais continuam pela busca local.

NCM, HS6 e descrições retornados são sempre lidos do catálogo. A IA só pode
selecionar candidatos fornecidos pelo backend. A existência do código é
validada, mas a associação continua sendo uma sugestão de pesquisa e exige
que o usuário confira a descrição e as características do produto.
Nenhum score de exportação é modificado por essa associação.

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
