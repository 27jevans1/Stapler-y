FROM ollama/ollama:latest

FROM python:latest

WORKDIR /

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "ai.py"]