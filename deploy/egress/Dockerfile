FROM alpine:3.20
RUN apk add --no-cache tinyproxy
COPY tinyproxy.conf allowlist /etc/tinyproxy/
USER tinyproxy
EXPOSE 8888
CMD ["tinyproxy", "-d", "-c", "/etc/tinyproxy/tinyproxy.conf"]
