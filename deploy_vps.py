import paramiko
import time
import os
import sys
import io
from dotenv import load_dotenv

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

load_dotenv()

HOST = os.getenv("VPS_HOST", "")
USER = os.getenv("VPS_USER", "root")
PASSWORD = os.getenv("VPS_PASSWORD", "")
REPO = "https://github.com/skislyakow/PythonMeetup.git"
DIR = "/opt/pythonmeetup"


def run(cmd, client, timeout=60):
    stdin, stdout, stderr = client.exec_command(cmd, timeout=timeout)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    return exit_code, out, err


def step(msg):
    print(f"\n{'='*60}")
    print(f"  {msg}")
    print(f"{'='*60}")


def connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    step("Подключение к VPS")
    client.connect(HOST, username=USER, password=PASSWORD, timeout=30, banner_timeout=30, look_for_keys=False, allow_agent=False)
    print("Connected")
    return client


def deploy():
    client = connect()

    try:
        step("Установка Python и Git")
        ec, out, err = run("apt update -qq && apt install -y -qq python3 python3-venv python3-pip git", client, timeout=120)
        print(out[-200:] if len(out) > 200 else out)
        print(err[-200:] if len(err) > 200 else err)
        print(f"Exit: {ec}")

        step("Создание директории проекта")
        ec, out, err = run(f"mkdir -p {DIR}", client)
        print(f"Exit: {ec}")

        step("Клонирование репозитория")
        ec, out, err = run(f"cd {DIR} && git clone {REPO} .", client, timeout=60)
        print(out[-300:] if len(out) > 300 else out)
        print(err[-300:] if len(err) > 300 else err)
        print(f"Exit: {ec}")

        step("Создание виртуального окружения")
        ec, out, err = run(f"cd {DIR} && python3 -m venv venv", client, timeout=30)
        print(f"Exit: {ec}")

        step("Установка зависимостей")
        ec, out, err = run(f"cd {DIR} && venv/bin/pip install -r requirements.txt", client, timeout=120)
        print(out[-200:] if len(out) > 200 else out)
        print(err[-200:] if len(err) > 200 else err)
        print(f"Exit: {ec}")

        step("Копирование .env.example в .env")
        ec, out, err = run(f"cp {DIR}/.env.example {DIR}/.env", client)
        print(f"Exit: {ec}")

        step("Миграции Django")
        ec, out, err = run(f"cd {DIR} && venv/bin/python manage.py migrate", client, timeout=30)
        print(out)
        print(err)
        print(f"Exit: {ec}")

        step("Сид тестовых данных")
        ec, out, err = run(f"cd {DIR} && venv/bin/python -m bot.seed", client, timeout=15)
        print(out)
        print(err)
        print(f"Exit: {ec}")

        step("Создание systemd-сервиса")
        service_content = f"""[Unit]
Description=PythonMeetup Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory={DIR}
ExecStart={DIR}/venv/bin/python -m bot.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
"""
        stdin, stdout, stderr = client.exec_command(f"cat > /etc/systemd/system/pythonmeetup.service")
        stdin.write(service_content)
        stdin.channel.shutdown_write()
        exit_code = stdout.channel.recv_exit_status()
        print(f"Service file created, exit: {exit_code}")

        step("Включение и запуск сервиса")
        ec, out, err = run("systemctl daemon-reload", client)
        ec, out, err = run("systemctl enable --now pythonmeetup", client, timeout=10)
        print(out)
        print(err)
        print(f"Exit: {ec}")

        step("Статус сервиса")
        ec, out, err = run("systemctl status pythonmeetup --no-pager -l", client)
        print(out[:500] if len(out) > 500 else out)
        print(f"Exit: {ec}")

        print(f"\n{'='*60}")
        print("Деплой завершён!")
        print(f"Проект: {DIR}")
        print(f".env нужно отредактировать: nano {DIR}/.env")
        print(f"Перезапуск: systemctl restart pythonmeetup")
        print(f"Логи: journalctl -u pythonmeetup -f")
        print(f"{'='*60}")

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        client.close()


def update():
    client = connect()

    try:
        step("git pull")
        ec, out, err = run(f"cd {DIR} && git pull", client, timeout=30)
        print(out)
        print(err[:300] if len(err) > 300 else err)
        print(f"Exit: {ec}")

        step("Обновление зависимостей")
        ec, out, err = run(f"cd {DIR} && venv/bin/pip install -r requirements.txt", client, timeout=120)
        print(out[-200:] if len(out) > 200 else out)
        print(err[-200:] if len(err) > 200 else err)
        print(f"Exit: {ec}")

        step("Миграции Django")
        ec, out, err = run(f"cd {DIR} && venv/bin/python manage.py migrate", client, timeout=30)
        print(out)
        print(err)
        print(f"Exit: {ec}")

        step("Рестарт сервиса")
        ec, out, err = run("systemctl restart pythonmeetup", client, timeout=10)
        print(f"Exit: {ec}")

        step("Статус сервиса")
        ec, out, err = run("systemctl status pythonmeetup --no-pager -l", client)
        print(out[:500] if len(out) > 500 else out)
        print(f"Exit: {ec}")

        print(f"\n{'='*60}")
        print("Обновление завершено!")
        print(f"Логи: journalctl -u pythonmeetup -f")
        print(f"{'='*60}")

    except Exception as e:
        print(f"Ошибка: {e}")
    finally:
        client.close()


if __name__ == "__main__":
    if not HOST or not PASSWORD:
        print("Ошибка: VPS_HOST и VPS_PASSWORD должны быть в .env")
        sys.exit(1)

    if "--update" in sys.argv:
        update()
    else:
        deploy()
