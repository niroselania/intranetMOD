FROM python:3.12-alpine
RUN pip install --no-cache-dir pyyaml
WORKDIR /app
COPY api/app.py /app/app.py
# Configuración inicial: se copia al volumen solo si todavía no existe
COPY config /seed
ENV PYTHONUNBUFFERED=1
EXPOSE 8000
CMD ["python", "/app/app.py"]
