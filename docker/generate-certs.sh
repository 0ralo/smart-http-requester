#!/bin/sh

# Install openssl if not present
if ! command -v openssl >/dev/null 2>&1; then
    echo "Installing openssl..."
    apk add --no-cache openssl
fi

CERT_DIR=/certs
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"

if [ -f ca.crt ] && [ -f rabbitmq.crt ]; then
  echo "Certificates already exist, skipping generation"
  exit 0
fi

echo "Generating CA..."
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -subj "/C=US/ST=State/L=Local/O=Dev CA/CN=dev-ca" -out ca.crt

# Helper to create and sign certs
create_cert () {
  NAME=$1
  CN=$2
  echo "Generating certificate for $NAME..."
  openssl genrsa -out ${NAME}.key 2048
  openssl req -new -key ${NAME}.key -subj "/C=US/ST=State/L=Local/O=Dev/CN=${CN}" -out ${NAME}.csr
  openssl x509 -req -in ${NAME}.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out ${NAME}.crt -days 3650 -sha256
  rm -f ${NAME}.csr
}

create_cert postgres postgres
create_cert redis redis
create_cert rabbitmq rabbitmq

# Combine cert+key for agents that expect a single pem
cat postgres.crt postgres.key > postgres.pem 2>/dev/null || true
cat rabbitmq.crt rabbitmq.key > rabbitmq.pem 2>/dev/null || true
cat redis.crt redis.key > redis.pem 2>/dev/null || true

chmod 644 *.crt *.pem *.key 2>/dev/null || true

echo "Certificates generated successfully in $CERT_DIR"
ls -la $CERT_DIR