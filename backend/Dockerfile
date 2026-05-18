FROM python:3.11-slim

# WeasyPrint system deps + LibreOffice for EMF/WMF/OMML conversion
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info \
    libreoffice \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Single worker + threads keeps LibreOffice subprocesses serialised;
# 120s timeout covers slow EMF/WMF conversion on first request.
CMD ["sh", "-c", "gunicorn app:app --bind 0.0.0.0:${PORT:-10000} --timeout 120 --workers 1 --threads 4"]
