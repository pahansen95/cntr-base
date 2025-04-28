#!/bin/bash
#
# Certificate Generation Script for OpenAI API Gateway
# Generates a self-signed TLS certificate for local development
#

set -e  # Exit on any error

# Default values - can be overridden with environment variables
CERT_PATH=${CERT_PATH:-"cert.pem"}
KEY_PATH=${KEY_PATH:-"key.pem"}
DAYS=${DAYS:-365}
CN=${CN:-"localhost"}
RSA_BITS=${RSA_BITS:-4096}

# Text formatting
BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

# Banner
echo -e "${BOLD}OpenAI API Gateway - Certificate Generator${RESET}"
echo "This script will generate a self-signed TLS certificate for local development."
echo

# Check for OpenSSL
if ! command -v openssl &> /dev/null; then
    echo -e "${RED}Error: OpenSSL is not installed or not in your PATH.${RESET}"
    echo "Please install OpenSSL and try again."
    exit 1
fi

# Show configuration
echo -e "${BOLD}Configuration:${RESET}"
echo -e "  Certificate Path: ${YELLOW}$CERT_PATH${RESET}"
echo -e "  Key Path:         ${YELLOW}$KEY_PATH${RESET}"
echo -e "  Validity:         ${YELLOW}$DAYS days${RESET}"
echo -e "  Common Name:      ${YELLOW}$CN${RESET}"
echo -e "  RSA Key Size:     ${YELLOW}$RSA_BITS bits${RESET}"
echo

# Check if files already exist
if [ -f "$CERT_PATH" ] || [ -f "$KEY_PATH" ]; then
    echo -e "${YELLOW}Warning: Certificate or key file already exists.${RESET}"
    read -p "Do you want to overwrite them? (y/N): " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Certificate generation aborted."
        exit 0
    fi
fi

# Generate the certificate
echo "Generating self-signed certificate..."
openssl req -x509 \
    -newkey rsa:$RSA_BITS \
    -keyout "$KEY_PATH" \
    -out "$CERT_PATH" \
    -days $DAYS \
    -nodes \
    -subj "/CN=$CN" \
    -addext "subjectAltName=DNS:$CN,DNS:localhost,IP:127.0.0.1"

# Check if generation was successful
if [ $? -eq 0 ] && [ -f "$CERT_PATH" ] && [ -f "$KEY_PATH" ]; then
    # Set permissions
    chmod 600 "$KEY_PATH"
    chmod 644 "$CERT_PATH"
    
    echo -e "\n${GREEN}Certificate generation completed successfully!${RESET}"
    echo
    echo -e "${BOLD}Certificate Information:${RESET}"
    openssl x509 -in "$CERT_PATH" -noout -text | grep -E 'Subject:|Issuer:|Not Before:|Not After :|DNS:|IP Address:'
    echo
    echo -e "${BOLD}Next Steps:${RESET}"
    echo "1. Run your OpenAI API Gateway with these certificates:"
    echo "   python gateway.py"
    echo
    echo "2. When using this self-signed certificate, your client may need to:"
    echo "   - Skip certificate validation (for testing only)"
    echo "   - Add this certificate to trusted certificates"
    echo
    echo -e "${YELLOW}Note: This certificate is for development purposes only.${RESET}"
    echo -e "${YELLOW}      Do not use it in production environments.${RESET}"
else
    echo -e "${RED}Error: Certificate generation failed.${RESET}"
    exit 1
fi