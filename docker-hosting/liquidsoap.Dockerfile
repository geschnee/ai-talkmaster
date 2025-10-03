FROM savonet/liquidsoap:v2.4.0

USER root

# Install netstat and other network tools
RUN apt-get update && \
    apt-get install -y net-tools procps telnet && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Create necessary directories
RUN mkdir -p /scripts /var/log/liquidsoap

# Copy liquidsoap scripts
COPY ./liquidsoap/start-stop-server.liq /scripts/start-stop-server.liq

COPY ./fallback-audio /fallback-audio

# Set proper permissions
RUN chown -R liquidsoap:liquidsoap /scripts /var/log/liquidsoap

USER liquidsoap
WORKDIR /home/liquidsoap

# Start liquidsoap with telnet server enabled
#CMD ["liquidsoap", "--interactive", "--telnet", "0.0.0.0:1234", "/scripts/start-stop-server.liq"]
CMD ["liquidsoap", "/scripts/start-stop-server.liq"]