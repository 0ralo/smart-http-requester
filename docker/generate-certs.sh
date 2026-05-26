#!/bin/sh
set -e
CERT_DIR=/certs
mkdir -p "$CERT_DIR"
cd "$CERT_DIR"
if [ -f ca.crt ]; then
  echo "Certificates already exist, skipping generation"
  exit 0
fi
# generate CA
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 3650 -subj "/C=US/ST=State/L=Local/O=Dev CA/CN=dev-ca" -out ca.crt

# Helper to create and sign certs
create_cert () {
  NAME=$1
  CN=$2
  openssl genrsa -out ${NAME}.key 2048
  openssl req -new -key ${NAME}.key -subj "/C=US/ST=State/L=Local/O=Dev/CN=${CN}" -out ${NAME}.csr
  openssl x509 -req -in ${NAME}.csr -CA ca.crt -CAkey ca.key -CAcreateserial -out ${NAME}.crt -days 3650 -sha256
}

create_cert postgres postgres
create_cert redis redis
create_cert rabbit rabbit

# Combine cert+key for agents that expect a single pem
cat postgres.crt postgres.key > postgres.pem || true
cat rabbit.crt rabbit.key > rabbit.pem || true
cat redis.crt redis.key > redis.pem || true

chmod 644 *.crt *.pem ca.key ca.crt
chmod 600 *.key || true

echo "Certificates generated in $CERT_DIR"
