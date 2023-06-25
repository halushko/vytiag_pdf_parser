FROM python:3.9-slim

WORKDIR /app
COPY main.py .
RUN mkdir /app/files

RUN pip install PyPDF2 python-telegram-bot

CMD ["python", "main.py"]