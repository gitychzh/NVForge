FROM python:3.11-slim
WORKDIR /app
RUN pip install --no-cache-dir PySocks==1.7.1
COPY proxy_server.py /app/proxy_server.py
EXPOSE 41104
ENTRYPOINT ["python3", "/app/proxy_server.py"]
