# Usar imagem base do Python
FROM python:3.10-slim

# Instalar FFmpeg e dependências do sistema
RUN apt-get update && \
    apt-get install -y ffmpeg && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Definir diretório de trabalho
WORKDIR /app

# Copiar arquivos de requisitos e instalar
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
RUN pip install fastapi uvicorn python-multipart

# Copiar o restante do código
COPY . .

# Expôr a porta que o Railway usa
EXPOSE 8080

# Comando para rodar a aplicação
CMD ["python", "server.py"]
