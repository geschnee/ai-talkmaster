FROM moul/icecast:latest

COPY ./docker-hosting/icecast.xml /etc/icecast2/icecast.xml

# The other parameters, e.g. ICECAST_SOURCE_PASSWORD are set in the CMD line of https://github.com/moul/docker-icecast/blob/master/Dockerfile#L17