FROM savonet/liquidsoap:v2.4.0

USER root

# Install netstat and other network tools
RUN apt-get update && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /scripts /var/log/liquidsoap

# Copy liquidsoap scripts
COPY ./start-stop-server-request-queue-http.liq /scripts/start-stop-server.liq

COPY ./fallback-audio /fallback-audio

# Set proper permissions
RUN chown -R liquidsoap:liquidsoap /scripts /var/log/liquidsoap

USER liquidsoap
WORKDIR /home/liquidsoap

CMD ["liquidsoap", "/scripts/start-stop-server.liq"]