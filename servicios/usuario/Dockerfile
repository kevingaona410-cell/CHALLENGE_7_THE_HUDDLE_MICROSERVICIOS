FROM python:3.11-slim

WORKDIR /app

COPY servicios/usuario/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt


COPY servicios/usuario/ .
COPY shared/ ./shared/

EXPOSE 5000

CMD ["python", "app.py"]