FROM python:latest

WORKDIR /

COPY . .

RUN pip install -r requirements.txt

CMD ["python", "main.py"]