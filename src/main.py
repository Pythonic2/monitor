from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from datetime import datetime, timezone
from src.models import MachineStatus
from tortoise.contrib.fastapi import register_tortoise
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(title="Monitor MVP")


# -------------------------------------------------------------------------
# SCHEMA / PAYLOAD DO AGENTE
# -------------------------------------------------------------------------
class Heartbeat(BaseModel):
    client_id: str
    machine_id: str
    running_programs: list[str]


# -------------------------------------------------------------------------
# ENDPOINT: AGENTE ENVIA HEARTBEAT
# -------------------------------------------------------------------------
@app.post("/heartbeat")
async def heartbeat(data: Heartbeat):
    now = datetime.now(timezone.utc)

    record, _ = await MachineStatus.get_or_create(
        machine_id=data.machine_id,
        defaults={
            "client_id": data.client_id,
            "running_programs": data.running_programs,
            "last_seen": now,
        },
    )

    # Atualiza
    record.running_programs = data.running_programs
    record.last_seen = now
    await record.save()

    return {"msg": "ok"}


# -------------------------------------------------------------------------
# API ENDPOINT PARA DADOS DO DASHBOARD
# -------------------------------------------------------------------------
@app.get("/api/machines")
async def get_machines_data():
    machines = await MachineStatus.all()
    now = datetime.now(timezone.utc)
    response_data = []

    for m in machines:
        if m.last_seen:
            last_seen = (
                m.last_seen
                if m.last_seen.tzinfo
                else m.last_seen.replace(tzinfo=timezone.utc)
            )
            delta = (now - last_seen).total_seconds()
            last_seen_text = last_seen.strftime("%Y-%m-%d %H:%M:%S")
        else:
            delta = 9999
            last_seen_text = "Nunca"

        status = "ONLINE" if delta < 30 else "OFFLINE"

        response_data.append(
            {
                "client_id": m.client_id,
                "machine_id": m.machine_id,
                "last_seen": last_seen_text,
                "status": status,
                "running_programs": ", ".join(m.running_programs or []),
            }
        )
    return response_data


# -------------------------------------------------------------------------
# DASHBOARD HTML
# -------------------------------------------------------------------------
@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Monitoramento - CloudBooster</title>
        <style>
            body { font-family: Arial; background: #eef2f3; padding: 20px; }
            table { width: 100%; border-collapse: collapse; background: white; box-shadow: 0 0 10px #ccc; }
            th, td { padding: 10px 12px; border: 1px solid #ddd; text-align: center; }
            th { background: #222; color: white; }
            .ok { color: green; font-weight: bold; }
            .offline { color: red; font-weight: bold; }
            h2 { font-size: 24px; }
        </style>
    </head>
    <body>
        <h2>Monitoramento de Máquinas - CloudBooster</h2>
        <p>Atualização automática a cada 5 segundos</p>
        <table>
            <thead>
                <tr>
                    <th>Cliente</th>
                    <th>Máquina</th>
                    <th>Último Sinal</th>
                    <th>Status</th>
                    <th>Programas Ativos</th>
                </tr>
            </thead>
            <tbody id="machines-table-body">
                <!-- Os dados serão inseridos aqui pelo JavaScript -->
            </tbody>
        </table>

        <script>
            async function updateTable() {
                const response = await fetch('/api/machines');
                const machines = await response.json();
                const tableBody = document.getElementById('machines-table-body');
                
                // Limpa a tabela antes de adicionar novos dados
                tableBody.innerHTML = '';

                machines.forEach(m => {
                    const statusClass = m.status === 'ONLINE' ? 'ok' : 'offline';
                    const row = `
                        <tr>
                            <td>${m.client_id}</td>
                            <td>${m.machine_id}</td>
                            <td>${m.last_seen}</td>
                            <td class="${statusClass}">${m.status}</td>
                            <td>${m.running_programs}</td>
                        </tr>
                    `;
                    tableBody.innerHTML += row;
                });
            }

            // Atualiza a tabela na carga da página e depois a cada 5 segundos
            document.addEventListener('DOMContentLoaded', () => {
                updateTable();
                setInterval(updateTable, 5000);
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(html)


# -------------------------------------------------------------------------
# CONFIGURAÇÃO TORTOISE ORM + POSTGRES
# -------------------------------------------------------------------------
TORTOISE_ORM = {
    "connections": {
        "default": {
            "engine": "tortoise.backends.asyncpg",
            "credentials": {
                "host": os.getenv("DB_HOST"),
                "port": os.getenv("DB_PORT"),
                "user": os.getenv("DB_USER"),
                "password": os.getenv("DB_PASSWORD"),
                "database": os.getenv("DB_NAME"),
                "server_settings": {"search_path": os.getenv("DB_SCHEMA")},
            },
        }
    },
    "apps": {
        "models": {
            "models": ["src.models"],
            "default_connection": "default",
        }
    },
}

register_tortoise(
    app,
    config=TORTOISE_ORM,
    generate_schemas=True,
    add_exception_handlers=True,
)


# -------------------------------------------------------------------------
# REDIRECIONAR / → /dashboard
# -------------------------------------------------------------------------
@app.get("/")
async def home():
    return RedirectResponse(url="/dashboard")
