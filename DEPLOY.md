# Загрузка проекта на сервер

Краткая инструкция по развёртыванию системы аналитики Ozon на Linux-сервере.

## 1. Загрузка файлов на сервер

### Вариант A: через Git (рекомендуется)

Если проект уже в репозитории (GitHub, GitLab и т.д.):

```bash
# На сервере
git clone https://github.com/ВАШ_ЛОГИН/analytic_number_cordusV2.git
cd analytic_number_cordusV2
```

### Вариант B: через SCP (с вашего ПК)

```bash
# Из папки проекта на Windows (PowerShell) или с родительской папки:
scp -r analytic_number_cordusV2 user@IP_СЕРВЕРА:/home/user/
```

Замените `user` на имя пользователя, `IP_СЕРВЕРА` — на IP или домен сервера.

### Вариант C: через SFTP (FileZilla, WinSCP и т.д.)

1. Подключитесь к серверу по SFTP (хост, порт 22, логин/пароль или ключ).
2. Загрузите всю папку проекта в нужный каталог на сервере (например `/home/user/analytic_number_cordusV2`).
3. Папку `upload/` с большими файлами можно не загружать, если отчёты будете заливать позже через UI.

---

## 2. Настройка окружения на сервере

Подключитесь по SSH и выполните:

```bash
cd /путь/к/analytic_number_cordusV2

# Python 3.10+ должен быть установлен
python3 --version

# Виртуальное окружение
python3 -m venv venv
source venv/bin/activate   # Linux/macOS

# Зависимости
pip install -r requirements.txt

# Для продакшена — WSGI-сервер
pip install gunicorn
```

---

## 3. Переменные окружения (продакшен)

Создайте файл `.env` в корне проекта (или задайте переменные в systemd/панели):

```bash
# Обязательно смените в продакшене
export FLASK_SECRET_KEY="длинный-случайный-секрет-ключ"

# Опционально
export OZON_API_BASE_URL="https://api-seller.ozon.ru"
```

Сгенерировать секрет: `python3 -c "import secrets; print(secrets.token_hex(32))"`.

---

## 4. Запуск приложения

### Режим разработки (для проверки)

```bash
source venv/bin/activate
python app.py
```

Сайт будет доступен по `http://IP_СЕРВЕРА:5000`.

### Режим продакшена (gunicorn)

```bash
source venv/bin/activate
gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
```

- `-w 4` — 4 воркера (подстройте под число ядер).
- `--timeout 120` — увеличенный таймаут для тяжёлых отчётов.

---

## 5. Запуск как службы (systemd)

Чтобы приложение поднималось после перезагрузки и перезапускалось при падении:

1. Создайте файл (подставьте свой путь и пользователя):

```bash
sudo nano /etc/systemd/system/ozon-analytics.service
```

2. Содержимое:

```ini
[Unit]
Description=Ozon Analytics Flask App
After=network.target

[Service]
User=ВАШ_ПОЛЬЗОВАТЕЛЬ
Group=ВАШ_ПОЛЬЗОВАТЕЛЬ
WorkingDirectory=/путь/к/analytic_number_cordusV2
Environment="PATH=/путь/к/analytic_number_cordusV2/venv/bin"
EnvironmentFile=/путь/к/analytic_number_cordusV2/.env
ExecStart=/путь/к/analytic_number_cordusV2/venv/bin/gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Включите и запустите:

```bash
sudo systemctl daemon-reload
sudo systemctl enable ozon-analytics
sudo systemctl start ozon-analytics
sudo systemctl status ozon-analytics
```

Логи: `journalctl -u ozon-analytics -f`.

---

## 6. Доступ с интернета (опционально)

- **Файрвол:** откройте порт 5000, если хотите пускать трафик напрямую:
  ```bash
  sudo ufw allow 5000
  sudo ufw reload
  ```
- **Nginx как обратный прокси** (порт 80/443, SSL):
  - Установите nginx, настройте `server` с `proxy_pass http://127.0.0.1:5000`.
  - Для HTTPS используйте Let's Encrypt (certbot).

---

## 7. Что проверить после загрузки

1. Папки `data/` и `upload/` создаются при первом запуске (или создайте вручную: `mkdir -p data upload`).
2. Файл `config.py` не требует правки для базового запуска; пути относительные.
3. Ключи Ozon API вводятся через веб-интерфейс и хранятся в сессии (не в коде).
4. Для тяжёлых отчётов и Selenium (если используется) убедитесь, что на сервере достаточно RAM и при необходимости установлен headless Chrome/Chromium.

---

## Краткий чеклист

| Шаг | Действие |
|-----|----------|
| 1 | Загрузить проект (Git / SCP / SFTP) |
| 2 | `python3 -m venv venv && source venv/bin/activate` |
| 3 | `pip install -r requirements.txt && pip install gunicorn` |
| 4 | Задать `FLASK_SECRET_KEY` в `.env` |
| 5 | Запустить: `gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 app:app` или настроить systemd |

После этого откройте в браузере: `http://IP_ВАШЕГО_СЕРВЕРА:5000`.
