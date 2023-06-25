FROM python:3.9-slim

WORKDIR /app
COPY main.py .

RUN pip install PyPDF2

CMD ["python", "main.py"]