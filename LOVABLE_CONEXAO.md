# Conexao do Lovable com o backend ExportAI

## API local

Enquanto o backend estiver rodando nesta maquina:

```text
http://127.0.0.1:8000
```

Swagger:

```text
http://127.0.0.1:8000/docs
```

## Endpoint principal

```text
POST http://127.0.0.1:8000/api/v1/recomendacoes
```

Exemplo de corpo:

```json
{
  "ncm": "09011110",
  "paises_ja_exportados": ["Argentina", "Estados Unidos", "Chile"],
  "quantidade": 5,
  "confianca_minima": "LIMITADA",
  "somente_novas": false
}
```

## Prompt para colar no Lovable

Conecte este frontend ao backend FastAPI do ExportAI.

Use a base URL configuravel por variavel de ambiente `VITE_EXPORTAI_API_URL`. Se ela nao existir, use `http://127.0.0.1:8000` como fallback local.

Crie um cliente de API centralizado para:

- `GET /health`
- `GET /api/v1/paises`
- `POST /api/v1/recomendacoes`
- `POST /api/v1/explicacao`

No formulario de recomendacao, envie:

- `ncm` com 8 digitos ou `hs6` com 6 digitos, nunca os dois ao mesmo tempo;
- `paises_ja_exportados` como lista de nomes;
- `quantidade`;
- `confianca_minima`;
- `somente_novas`.

Mostre os campos retornados em `recomendacoes`: ranking, pais, ISO3, score_exportai, indice_cobertura, faixa_confianca, tipo_oportunidade, motivo_recomendacao e os scores usados. Se a API retornar erro, mostre `detail.erro.mensagem`.

Adicione em cada card de pais um botao chamado `Explicar com IA`. Ao clicar,
envie para `POST /api/v1/explicacao` o objeto `consulta` retornado pela busca e
a `recomendacao` daquele pais. Mostre `explicacao` dentro de um card, modal ou
accordion abaixo do pais. Mostre discretamente o aviso retornado pela API:
`A IA apenas explica os dados calculados pelo motor ExportAI; ela nao recalcula
nem altera o score.`

## Exemplo de cliente TypeScript

```ts
const API_URL = import.meta.env.VITE_EXPORTAI_API_URL ?? "http://127.0.0.1:8000";

export async function consultarRecomendacoes(payload: {
  ncm?: string;
  hs6?: string;
  paises_ja_exportados: string[];
  quantidade: number;
  confianca_minima: "LIMITADA" | "MODERADA" | "ALTA";
  somente_novas: boolean;
}) {
  const resposta = await fetch(`${API_URL}/api/v1/recomendacoes`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => null);
    throw new Error(erro?.detail?.erro?.mensagem ?? "Falha ao consultar o ExportAI.");
  }

  return resposta.json();
}

export async function explicarRecomendacao(payload: {
  consulta: unknown;
  recomendacao: unknown;
}) {
  const resposta = await fetch(`${API_URL}/api/v1/explicacao`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!resposta.ok) {
    const erro = await resposta.json().catch(() => null);
    throw new Error(erro?.detail?.erro?.mensagem ?? "Falha ao explicar a recomendacao.");
  }

  return resposta.json() as Promise<{
    explicacao: string;
    origem: "groq" | "openai" | "fallback_local";
    aviso: string;
  }>;
}
```

## Prompt para adicionar a explicacao no Lovable

```text
Adicione explicacao com IA aos resultados do ExportAI.

Para cada card de recomendacao, inclua um botao "Explicar com IA". Ao clicar,
chame o endpoint POST `${API_URL}/api/v1/explicacao` enviando:

{
  "consulta": consultaDaResposta,
  "recomendacao": recomendacaoDoCard
}

Mostre a resposta `explicacao` em um accordion/card abaixo daquele pais. Mostre
um loading enquanto consulta. Se `origem` for "fallback_local", mostre um selo
discreto "explicacao local". Se for "groq" ou "openai", mostre "explicacao IA".

Importante: nao recalcule o score no frontend. A explicacao deve deixar claro
que a IA apenas interpreta os dados calculados pelo backend ExportAI.
```

## Observacao importante

O preview do Lovable pode chamar `http://127.0.0.1:8000` enquanto voce testa no seu navegador e o backend esta aberto na mesma maquina. Para publicar para outras pessoas, a API precisa estar em uma URL publica, como Render, Railway, Fly.io ou outro servidor.
