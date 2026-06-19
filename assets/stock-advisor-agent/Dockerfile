FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY app/ ./

ENV PORT=5000
ENV HOST=0.0.0.0

EXPOSE 5000

CMD ["python", "main.py", "--host", "0.0.0.0", "--port", "5000"]
