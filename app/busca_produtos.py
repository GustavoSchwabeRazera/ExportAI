"""Busca lexical aproximada no catálogo, sem inventar códigos ou produtos."""

from collections import defaultdict
from difflib import get_close_matches, SequenceMatcher
import re
import unicodedata


STOPWORDS = set("a as o os e de da das do dos em com para por um uma produto produtos quero exportar vender".split())

# Equivalências de linguagem comercial; não representam classificação fiscal.
# A comparação aproximada funciona para todo o vocabulário do catálogo.
GRUPOS = (
    ("linguica", "linguicas", "salsicha", "salsichas", "embutido", "embutidos", "enchido", "enchidos"),
    ("camiseta", "camisetas", "t shirt", "tshirt"),
    ("tenis", "sapato", "sapatos", "calcado", "calcados"),
    ("celular", "celulares", "smartphone", "smartphones", "telefone", "telefones"),
    ("notebook", "notebooks", "laptop", "laptops", "computador", "computadores"),
    ("geladeira", "geladeiras", "refrigerador", "refrigeradores"),
    ("carro", "carros", "automovel", "automoveis"),
    ("bike", "bikes", "bicicleta", "bicicletas"),
    ("oculos", "oculo"),
    ("mandioca", "aipim", "macaxeira"),
    ("amendoim", "amendoins"),
    ("suco", "sucos", "sumo", "sumos"),
    ("bolacha", "bolachas", "biscoito", "biscoitos"),
    ("manteiga", "manteigas"),
    ("pneu", "pneus", "pneumatico", "pneumaticos"),
    ("adubo", "adubos", "fertilizante", "fertilizantes"),
    ("remedio", "remedios", "medicamento", "medicamentos"),
    ("cachorro", "cachorros", "cao", "caes"),
)

# Expressões técnicas que não compartilham palavras com o nome popular.
EXPRESSOES = {
    "notebook": "processamento dados portateis",
    "notebooks": "processamento dados portateis",
    "laptop": "processamento dados portateis",
    "laptops": "processamento dados portateis",
    "geladeira": "refrigeradores domestico",
    "geladeiras": "refrigeradores domestico",
}


def normalizar(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto.casefold())
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", " ", texto).strip()


class BuscaCatalogo:
    """Índice em memória reutilizado para evitar varrer o catálogo a cada tecla."""

    def __init__(self, descricoes: list[str]) -> None:
        self.descricoes = descricoes
        self.indice: dict[str, set[int]] = defaultdict(set)
        for posicao, descricao in enumerate(descricoes):
            for palavra in set(descricao.split()) - STOPWORDS:
                self.indice[palavra].add(posicao)
        self.vocabulario = sorted(self.indice)
        self.sinonimos = {termo: grupo for grupo in GRUPOS for termo in grupo}

    def alternativas(self, palavra: str, prefixo: bool) -> dict[str, float]:
        """Exata > flexão/sinônimo > prefixo > erro de digitação."""
        candidatos = {palavra: 1.0}
        for termo in self.sinonimos.get(palavra, ()):
            for token in termo.split():
                candidatos[token] = max(candidatos.get(token, 0), 0.88)
        if len(palavra) >= 4:
            # Flexões comuns sem reduzir palavras curtas a radicais genéricos.
            for variante in (palavra.rstrip("s"), palavra + "s", palavra[:-3] + "ao" if palavra.endswith("oes") else palavra):
                candidatos[variante] = max(candidatos.get(variante, 0), 0.94)
        if prefixo and len(palavra) >= 3:
            for termo in self.vocabulario:
                if termo.startswith(palavra):
                    candidatos[termo] = max(candidatos.get(termo, 0), 0.82)
        # Termos curtos não recebem correção difusa: evita falsas associações.
        if len(palavra) >= 4 and not any(termo in self.indice for termo in candidatos):
            for termo in get_close_matches(palavra, self.vocabulario, n=4, cutoff=0.8 if len(palavra) >= 5 else 0.85):
                candidatos[termo] = max(candidatos.get(termo, 0), 0.75 * SequenceMatcher(None, palavra, termo).ratio())
        return candidatos

    def buscar(self, consulta: str) -> list[tuple[int, float]]:
        consulta = normalizar(consulta)
        consulta = " ".join(EXPRESSOES.get(p, p) for p in consulta.split())
        for grupo in GRUPOS:
            for termo in grupo:
                if " " in termo:
                    consulta = consulta.replace(termo, grupo[0])
        palavras = list(dict.fromkeys(p for p in consulta.split() if p not in STOPWORDS))
        if not palavras:
            return []
        notas: dict[int, list[float]] = {}
        for numero, palavra in enumerate(palavras):
            for alternativa, peso in self.alternativas(palavra, numero == len(palavras) - 1).items():
                for posicao in self.indice.get(alternativa, ()):
                    valores = notas.setdefault(posicao, [0.0] * len(palavras))
                    valores[numero] = max(valores[numero], peso)
        completos = [(p, v) for p, v in notas.items() if all(v)]
        # Só relaxa consultas longas quando a maioria dos termos está presente.
        # Uma palavra desconhecida sozinha nunca devolve produtos aleatórios.
        candidatos = completos or [(p, v) for p, v in notas.items() if len(palavras) >= 3 and sum(bool(x) for x in v) / len(palavras) >= 0.75]
        resultado = []
        for posicao, valores in candidatos:
            descricao = self.descricoes[posicao]
            nota = sum(valores) / len(palavras)
            inicio = set(descricao.split()[:2])
            nota += 0.15 * sum(bool(inicio & set(self.alternativas(p, False))) for p in palavras) / len(palavras)
            # Peças e insumos seguem disponíveis, mas ficam atrás do produto.
            if not set(palavras) & {"parte", "partes", "acessorio", "acessorios", "mistura", "misturas"}:
                if set(descricao.split()[:3]) & {"partes", "acessorios", "misturas"}:
                    nota -= 0.2
            if consulta in descricao:
                nota += 0.2
            if "nao" not in palavras:
                for palavra in palavras:
                    if re.search(r"\bnao " + re.escape(palavra) + r"\b", descricao):
                        nota -= 0.25
            resultado.append((posicao, nota))
        return sorted(resultado, key=lambda item: (-item[1], item[0]))
