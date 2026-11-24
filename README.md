# Lyftr AI Full-Stack Assignment

A full-stack LLM chatbot built with React, FastAPI, LiteLLM and SQLite. The application supports multi-turn conversations, automatic API-key failover, LiteLLM response caching, per-request token tracking and Docker-based local execution.

## 1. Live URLs

Frontend:
https://lyftr-ai-chatbot-frontend.onrender.com

Backend:
https://lyftr-ai-chatbot-backend-zpik.onrender.com

Backend Swagger Documentation:
https://lyftr-ai-chatbot-backend-zpik.onrender.com/docs

GitHub Repository:
https://github.com/anantpundir95-hash/lyftr-ai-chatbot

## 2. Run locally: with Docker and without

### With Docker

Create a `.env` file in the repository root using `.env.example` as a reference.

Set at least two Gemini API keys:

```env
LLM_API_KEYS=your_key_1,your_key_2
LLM_MODEL=gemini/gemini-3.5-flash-lite