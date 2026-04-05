FROM python:3.11-slim

WORKDIR /app

COPY servicios/inventario/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY servicios/inventario/ .
COPY shared/ ./shared/

EXPOSE 5002

CMD ["python", "app.py"]