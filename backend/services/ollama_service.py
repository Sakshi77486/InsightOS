import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5-coder:7b"


def generate_insight(prompt: str):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 2000
            }
        },
        timeout=1000
    )

    response.raise_for_status()

    return response.json()["response"]


def generate_chat_response(prompt: str):
    response = requests.post(
        OLLAMA_URL,
        json={
            "model": MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.2,
                "num_predict": 2000
            }
        },
        timeout=1000
    )

    response.raise_for_status()

    return response.json()["response"]