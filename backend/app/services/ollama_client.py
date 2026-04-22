import os
import json
import re
from collections.abc import AsyncIterator

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:0.6b")


class OllamaClientError(RuntimeError):
    pass


PARAGRAPH_LABEL_PATTERN = re.compile(r"^\s*par[aá]grafo\s*\d+\s*:\s*", re.IGNORECASE)


def _remove_paragraph_labels(text: str) -> str:
    lines = text.splitlines()
    return "\n".join(PARAGRAPH_LABEL_PATTERN.sub("", line) for line in lines)


def sanitize_commentary(text: str) -> str:
    sanitized = _remove_paragraph_labels(text)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    return sanitized.strip()


def sanitize_commentary_chunk(text: str) -> str:
    return _remove_paragraph_labels(text)


def build_commentary_prompt(race_title: str, podium_text: str, top10_text: str) -> str:
    return f"""
Você é um comentarista brasileiro de Fórmula 1.
Escreva um comentário curto, natural e fluido sobre {race_title}, em português do Brasil.

Regras obrigatórias:
- escreva 2 parágrafos curtos
- soe humano e jornalístico, não robótico
- cite os 3 pilotos do pódio no primeiro parágrafo
- cite 2 ou 3 destaques reais do top-10 no segundo parágrafo
- use apenas os dados fornecidos
- não invente disputa de campeonato, estratégia, ultrapassagens ou contexto externo
- não diga frases vagas como "as implicações para o futuro" ou "a dinâmica do torneio"
- não repita a lista completa de posições
- não escreva marcadores como "Parágrafo 1:", "Parágrafo 2:", "Primeiro parágrafo:" ou similares
- prefira observações concretas sobre quem venceu, quem completou o pódio e quais equipes apareceram bem
- use pontuação e espaçamento normais entre todas as palavras
- nunca junte várias palavras sem espaço
- mantenha entre 70 e 110 palavras no total

Estrutura:
- no primeiro parágrafo, resuma o resultado com foco no vencedor e no pódio
- no segundo parágrafo, faça uma leitura breve do top-10 destacando 2 ou 3 nomes/equipes
- entregue apenas o texto final, sem títulos, sem enumeração e sem rótulos de parágrafo

Pódio:
{podium_text}

Top-10:
{top10_text}
""".strip()


async def generate_commentary(race_title: str, podium_text: str, top10_text: str) -> str:
    prompt = build_commentary_prompt(race_title, podium_text, top10_text)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.7},
    }

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(f"{OLLAMA_BASE_URL}/api/generate", json=payload)
            response.raise_for_status()
            data = response.json()
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise OllamaClientError(
                f"Modelo Ollama não encontrado: {OLLAMA_MODEL}"
            ) from exc
        raise OllamaClientError("Falha ao consultar o Ollama") from exc
    except httpx.HTTPError as exc:
        raise OllamaClientError("Falha ao consultar o Ollama") from exc

    return sanitize_commentary(
        data.get("response", "Não foi possível gerar comentário no momento.")
    )


async def stream_commentary(
    race_title: str, podium_text: str, top10_text: str
) -> AsyncIterator[str]:
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": build_commentary_prompt(race_title, podium_text, top10_text),
        "stream": True,
        "options": {"temperature": 0.7},
    }

    try:
        async with httpx.AsyncClient(timeout=None) as client:
            async with client.stream(
                "POST",
                f"{OLLAMA_BASE_URL}/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    chunk = json.loads(line)
                    text = chunk.get("response")
                    if text:
                        yield sanitize_commentary_chunk(text)

                    if chunk.get("done"):
                        break
    except httpx.HTTPStatusError as exc:
        if exc.response.status_code == 404:
            raise OllamaClientError(
                f"Modelo Ollama não encontrado: {OLLAMA_MODEL}"
            ) from exc
        raise OllamaClientError("Falha ao consultar o Ollama") from exc
    except httpx.HTTPError as exc:
        raise OllamaClientError("Falha ao consultar o Ollama") from exc
