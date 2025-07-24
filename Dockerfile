# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies for Tesseract OCR
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-deu \
    tesseract-ocr-eng \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY main.py .

# Create directory for persistent data
RUN mkdir -p /app/data

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata

# Create non-root user for security
RUN useradd -m -u 1000 botuser && chown -R botuser:botuser /app
USER botuser

# Command to run the bot
CMD ["python", "main.py"]