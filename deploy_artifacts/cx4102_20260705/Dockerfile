FROM python:3.12-slim
# cx4102: 纯标准库 (http.server + http.client + json + threading), 无第三方依赖.
# 与 nv-gw 风格一致: 零依赖, 快速构建.
WORKDIR /app
RUN mkdir -p /app/logs
COPY gateway/ ./gateway/
COPY gateway_main.py .
ENV PYTHONUNBUFFERED=1
ENTRYPOINT ["python3"]
CMD ["gateway_main.py"]
