FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (incl. WeasyPrint for PDF reports: Pango, GObject, Cairo)
RUN apt-get update && apt-get install -y \
    postgresql-client \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    libgdk-pixbuf-2.0-0 \
    libglib2.0-0 \
    libcairo2 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8001

EXPOSE 8001

# Run the application
CMD ["uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8001"]
