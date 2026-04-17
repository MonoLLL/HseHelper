# Deploy

## Что уже подготовлено

Для production-развёртывания в проект добавлены:

- `docker-compose.prod.yml`
- `Caddyfile`
- `backend/Dockerfile.prod`
- `frontend/Dockerfile.prod`
- `bot/Dockerfile.prod`

## Что нужно для публичного запуска

1. VPS или другой сервер с публичным IP-адресом.
2. Домен, у которого `A`-запись указывает на этот сервер.
3. Открытые порты `80` и `443`.
4. Установленные Docker и Docker Compose plugin.

## Что заполнить перед запуском

В корневом `.env` должны быть корректные значения:

- `APP_DOMAIN=your-domain.example`
- `POSTGRES_DB`
- `POSTGRES_USER`
- `POSTGRES_PASSWORD`
- `MEILI_MASTER_KEY`
- `JWT_SECRET`
- `DEFAULT_ADMIN_EMAIL`
- `DEFAULT_ADMIN_PASSWORD`
- `DEFAULT_ADMIN_NAME`

Если Telegram-бот нужен в production, проверь и файл `bot/.env`.

## Как развернуть

1. Скопируйте проект на сервер.
2. Заполните `.env` и `bot/.env`.
3. Убедитесь, что домен уже смотрит на IP сервера.
4. Выполните:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

После этого:

- `caddy` поднимет публичный вход и попытается выпустить HTTPS-сертификат;
- `frontend` будет доступен снаружи;
- запросы на `/api` и `/uploads` будут проксироваться в `backend`.

## Быстрый сценарий для Ubuntu VPS

1. Подключитесь к серверу по SSH.
2. Установите Docker и Compose plugin.
3. Создайте папку проекта, например `/opt/kurs_project`.
4. Склонируйте туда репозиторий.
5. Создайте `.env` и `bot/.env`.
6. Запустите production-окружение.

Пример команд:

```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2 git
sudo systemctl enable --now docker

sudo mkdir -p /opt/kurs_project
sudo chown $USER:$USER /opt/kurs_project

git clone <YOUR_REPO_URL> /opt/kurs_project
cd /opt/kurs_project

cp .env.example .env
docker-compose -f docker-compose.prod.yml up -d --build
```

Если домен уже привязан к серверу, сайт после запуска будет доступен по `https://ваш-домен`.

## Автодеплой через GitHub Actions

В проект добавлен workflow:

- `.github/workflows/deploy.yml`

Он запускается:

- при `push` в ветку `main`;
- вручную через `workflow_dispatch`.

Что делает workflow:

1. Подключается к VPS по SSH.
2. Переходит в папку проекта на сервере.
3. Делает `git pull origin main`.
4. Выполняет `docker-compose -f docker-compose.prod.yml up -d --build`.

### Какие Secrets нужно добавить в GitHub

В репозитории откройте:

`Settings -> Secrets and variables -> Actions`

Добавьте:

- `VPS_HOST` — IP-адрес сервера.
- `VPS_USER` — пользователь на сервере, например `ubuntu`.
- `VPS_SSH_KEY` — приватный SSH-ключ для входа на сервер.
- `VPS_PORT` — порт SSH, обычно `22`.
- `PROJECT_PATH` — путь к проекту на сервере, например `/opt/kurs_project`.

### Как подготовить SSH-ключ

На локальной машине создайте ключ:

```bash
ssh-keygen -t ed25519 -C "github-deploy"
```

Дальше:

1. Содержимое публичного ключа добавьте на сервер в `~/.ssh/authorized_keys`.
2. Содержимое приватного ключа сохраните в GitHub Secret `VPS_SSH_KEY`.

## Рекомендуемый порядок запуска автодеплоя

1. Сначала один раз разверните проект вручную на сервере.
2. Убедитесь, что `docker-compose -f docker-compose.prod.yml up -d --build` работает без ошибок.
3. После этого добавьте GitHub Secrets.
4. Сделайте пуш в `main` и проверьте вкладку `Actions`.

Так проще отделить проблемы инфраструктуры от проблем CI/CD.

## Полезные команды

Проверить статус контейнеров:

```powershell
docker compose -f docker-compose.prod.yml ps
```

Посмотреть логи:

```powershell
docker compose -f docker-compose.prod.yml logs -f
```

Перезапустить только backend:

```powershell
docker compose -f docker-compose.prod.yml restart backend
```

Обновить проект после изменений:

```powershell
docker compose -f docker-compose.prod.yml up -d --build
```

## Что важно помнить

- Без домена HTTPS через Caddy автоматически не поднимется.
- Если сервер новый, проверьте firewall и security group: порты `80` и `443` должны быть доступны извне.
- Папка с загруженными файлами хранится в docker volume `uploads_data`, поэтому файлы не пропадут при перезапуске контейнеров.
- Для автодеплоя на сервере должны быть установлены `git`, `docker` и `docker-compose`.
