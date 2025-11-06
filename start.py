# start.py
import os
import uvicorn

# Timeweb передаёт порт в переменной окружения PORT
port = int(os.environ.get("PORT", "8000"))
uvicorn.run("app.server:app", host="0.0.0.0", port=port)
