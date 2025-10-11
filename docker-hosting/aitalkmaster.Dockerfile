# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app


# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*



# Copy requirements first for better caching
COPY ./aitalkmaster-server/requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt


# Copy the Python modules
COPY ./aitalkmaster-server .

COPY ./fallback-audio ./fallback-audio

# Create a non-root user for security
RUN useradd --create-home --shell /bin/bash app

RUN chown -R app:app /app

# Create necessary directories and set proper permissions
RUN mkdir -p generated-audio
USER app

# Expose the port
EXPOSE 7999

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:7999/statusAitalkmaster || exit 1

# Run the application
CMD ["python", "ai_talkmaster.py"]
#CMD ["ls", "-la"]
