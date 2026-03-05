FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source
COPY . .

# Create __init__.py files
RUN touch config/__init__.py utils/__init__.py llm/__init__.py \
    telegram/__init__.py email_agent/__init__.py calendar_agent/__init__.py \
    expenses/__init__.py tts/__init__.py knowledge/__init__.py \
    orchestrator/__init__.py

# Default: run orchestrator server
CMD ["uvicorn", "orchestrator.server:app", "--host", "0.0.0.0", "--port", "8000"]
