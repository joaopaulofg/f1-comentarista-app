import os
import json
from collections.abc import AsyncIterator

import httpx

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:1.7b")


class OllamaClientError(RuntimeError):
    pass


def build_commentary_prompt(race_title: str, podium_text: str, top10_text: str) -> str:
    return f"""
Você é um jornalista esportivo especialista em Fórmula 1.
Faça um comentário em português (Brasil), com até 3 parágrafos curtos,
sobre a corrida {race_title}.

Foque em:
1) pódio,
2) destaques do top-10,
3) resultado final e implicações.

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

    return data.get("response", "Não foi possível gerar comentário no momento.")


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
                        yield text

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
