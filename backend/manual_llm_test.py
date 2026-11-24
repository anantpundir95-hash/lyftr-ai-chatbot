import os

from dotenv import load_dotenv
from litellm import completion


load_dotenv()


keys = [
    key.strip()
    for key in os.getenv("LLM_API_KEYS", "").split(",")
    if key.strip()
]

model = os.getenv(
    "LLM_MODEL",
    "gemini/gemini-3.5-flash-lite"
)


print(f"Keys loaded: {len(keys)}")
print(f"Model: {model}")


if not keys:
    raise RuntimeError("No API keys configured")


response = completion(
    model=model,
    messages=[
        {
            "role": "user",
            "content": "Reply with exactly: Lyftr test successful"
        }
    ],
    api_key=keys[0]
)


print("AI response:")
print(response.choices[0].message.content)
