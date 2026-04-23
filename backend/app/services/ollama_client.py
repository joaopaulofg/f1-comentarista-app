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
META_OPENING_PATTERN = re.compile(
    r"^\s*(no|em)\s+(primeiro|segundo)\s+par[aá]grafo\s*,?\s*",
    re.IGNORECASE,
)


def _remove_paragraph_labels(text: str) -> str:
    lines = text.splitlines()
    cleaned_lines = []
    for line in lines:
        line = PARAGRAPH_LABEL_PATTERN.sub("", line)
        line = META_OPENING_PATTERN.sub("", line)
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def sanitize_commentary(text: str) -> str:
    sanitized = _remove_paragraph_labels(text)
    sanitized = re.sub(r"\n{3,}", "\n\n", sanitized)
    return sanitized.strip()


def sanitize_commentary_chunk(text: str) -> str:
    return _remove_paragraph_labels(text)


def build_commentary_prompt(race_title: str, podium_text: str, top10_text: str) -> str:
    return f"""
Escreva uma nota 2 paragrafos pós-corrida sobre {race_title}. Inicie comentando sobre a corrida no geral e depois foque no resultado do pódio. Depois, destaque 2 ou 3 nomes/equipes do top 10 que chamaram atenção. Mantenha o texto entre 80 e 100 palavras. Evite usar linguagem robótica ou formal demais. Use um tom de jornalista esportivo, natural, direto e concreto.

Idioma: português do Brasil.
Tom: jornalista esportivo, natural, direto e concreto.

Escreva somente o comentário final.
Não explique o que está fazendo.
Não use frases como:
- "No primeiro parágrafo"
- "No segundo parágrafo"
- "Parágrafo 1"
- "Parágrafo 2"
- "Em resumo"

Use apenas os dados abaixo.
Não invente estratégia, campeonato, ultrapassagens, clima, punições ou contexto externo.
Não transforme o texto em lista.
Não repita o top 10 inteiro.
Não use linguagem robótica.

Objetivo do texto:
- abrir com o vencedor e fechar o pódio
- depois destacar 2 ou 3 nomes/equipes do top 10 que chamam atenção
- manter o texto curto, com 2 blocos curtos e boa fluidez
- ficar entre 60 e 90 palavras

Escreva como se fosse uma nota publicada logo após a corrida.

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
