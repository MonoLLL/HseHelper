# Университетская система быстрых ответов (чат-бот + сайт + админка)

Монорепозиторий для дипломного проекта: единая база знаний (FAQ/события) + чат-бот + веб-сайт и простая админка для сотрудников учебного офиса.

Сервисы: backend (FastAPI) · bot (Telegram, aiogram) · frontend (Next.js) · db (схема) · docker-compose.yml

## Быстрый старт
1) Установите Docker + Docker Compose
2) Скопируйте `.env.example` в `.env` и при необходимости измените значения
3) `docker compose up --build`
4) Инициализация данных: `docker compose exec backend python -m app.seed`
5) Откройте:
- Backend: http://localhost:8000 (Swagger: /docs)
- Frontend: http://localhost:3000
- Meilisearch: http://localhost:7700
