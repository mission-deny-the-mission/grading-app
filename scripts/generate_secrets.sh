#!/bin/bash
# Generate Secrets Script
#
# Generates secure SECRET_KEY and DB_ENCRYPTION_KEY for the grading application.
# Validates secret strength and provides secure storage instructions.

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
MIN_SECRET_KEY_LENGTH=32
MIN_ENCRYPTION_KEY_LENGTH=44  # Base64-encoded 32-byte Fernet key

# Detect OS for sed compatibility
# macOS requires -i with extension (e.g., -i.bak)
# GNU sed (Linux) requires -i with optional extension after space (e.g., -i or -i .bak)
if [[ "$OSTYPE" == "darwin"* ]]; then
    SED_INPLACE=(-i.bak)
else
    SED_INPLACE=(-i)
fi

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  Grading App - Secrets Generator${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Function to generate SECRET_KEY
generate_secret_key() {
    echo -e "${YELLOW}Generating SECRET_KEY...${NC}"

    # Generate 32-byte (256-bit) secret key as hex string
    SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')

    if [ ${#SECRET_KEY} -lt $MIN_SECRET_KEY_LENGTH ]; then
        echo -e "${RED}ERROR: Generated SECRET_KEY is too short (${#SECRET_KEY} < $MIN_SECRET_KEY_LENGTH)${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ SECRET_KEY generated (${#SECRET_KEY} characters)${NC}"
    echo ""
}

# Function to generate DB_ENCRYPTION_KEY
generate_encryption_key() {
    echo -e "${YELLOW}Generating DB_ENCRYPTION_KEY...${NC}"

    # Generate Fernet-compatible encryption key
    DB_ENCRYPTION_KEY=$(python3 -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())')

    # Validate key
    python3 -c "from cryptography.fernet import Fernet; Fernet('$DB_ENCRYPTION_KEY'.encode())" 2>/dev/null

    if [ $? -ne 0 ]; then
        echo -e "${RED}ERROR: Generated encryption key is invalid${NC}"
        exit 1
    fi

    if [ ${#DB_ENCRYPTION_KEY} -lt $MIN_ENCRYPTION_KEY_LENGTH ]; then
        echo -e "${RED}ERROR: Generated DB_ENCRYPTION_KEY is too short (${#DB_ENCRYPTION_KEY} < $MIN_ENCRYPTION_KEY_LENGTH)${NC}"
        exit 1
    fi

    echo -e "${GREEN}✓ DB_ENCRYPTION_KEY generated (${#DB_ENCRYPTION_KEY} characters)${NC}"
    echo ""
}

# Function to validate secret strength
validate_secret_strength() {
    local secret=$1
    local name=$2

    echo -e "${YELLOW}Validating $name strength...${NC}"

    # Check length
    if [ ${#secret} -lt 32 ]; then
        echo -e "${RED}✗ Length too short (${#secret} < 32)${NC}"
        return 1
    fi

    # Check entropy (basic check - contains mixed characters)
    if [[ ! "$secret" =~ [A-Za-z] ]] || [[ ! "$secret" =~ [0-9] ]]; then
        echo -e "${RED}✗ Insufficient entropy (needs letters and numbers)${NC}"
        return 1
    fi

    echo -e "${GREEN}✓ $name is strong${NC}"
    return 0
}

# Function to display secrets
display_secrets() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Generated Secrets${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    echo -e "${YELLOW}SECRET_KEY:${NC}"
    echo "$SECRET_KEY"
    echo ""

    echo -e "${YELLOW}DB_ENCRYPTION_KEY:${NC}"
    echo "$DB_ENCRYPTION_KEY"
    echo ""
}

# Function to save to .env file
save_to_env() {
    local env_file=${1:-.env}

    echo -e "${YELLOW}Save secrets to $env_file? (y/N):${NC} "
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Backup existing .env if it exists
        if [ -f "$env_file" ]; then
            backup_file="${env_file}.backup.$(date +%Y%m%d_%H%M%S)"
            cp "$env_file" "$backup_file"
            echo -e "${GREEN}✓ Backed up existing $env_file to $backup_file${NC}"
        fi

        # Check if secrets already exist in .env
        if grep -q "^SECRET_KEY=" "$env_file" 2>/dev/null; then
            sed "${SED_INPLACE[@]}" "s|^SECRET_KEY=.*|SECRET_KEY=$SECRET_KEY|" "$env_file"
            echo -e "${GREEN}✓ Updated SECRET_KEY in $env_file${NC}"
        else
            echo "SECRET_KEY=$SECRET_KEY" >> "$env_file"
            echo -e "${GREEN}✓ Added SECRET_KEY to $env_file${NC}"
        fi

        if grep -q "^DB_ENCRYPTION_KEY=" "$env_file" 2>/dev/null; then
            sed "${SED_INPLACE[@]}" "s|^DB_ENCRYPTION_KEY=.*|DB_ENCRYPTION_KEY=$DB_ENCRYPTION_KEY|" "$env_file"
            echo -e "${GREEN}✓ Updated DB_ENCRYPTION_KEY in $env_file${NC}"
        else
            echo "DB_ENCRYPTION_KEY=$DB_ENCRYPTION_KEY" >> "$env_file"
            echo -e "${GREEN}✓ Added DB_ENCRYPTION_KEY to $env_file${NC}"
        fi

        # Clean up backup files created by sed on macOS
        if [[ "$OSTYPE" == "darwin"* ]]; then
            rm -f "${env_file}.bak"
        fi

        # Set restrictive permissions
        chmod 600 "$env_file"
        echo -e "${GREEN}✓ Set permissions on $env_file to 600 (owner read/write only)${NC}"
        echo ""
    fi
}

# Function to save to secure location
save_to_secure_location() {
    echo -e "${YELLOW}Save to secure backup location? (y/N):${NC} "
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        # Create secure directory if it doesn't exist
        SECURE_DIR="/etc/grading-app/secrets"

        if [ ! -d "$SECURE_DIR" ]; then
            echo -e "${YELLOW}Creating secure directory: $SECURE_DIR${NC}"
            sudo mkdir -p "$SECURE_DIR"
            sudo chmod 700 "$SECURE_DIR"
        fi

        # Save secrets
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)
        SECRET_FILE="$SECURE_DIR/secrets_$TIMESTAMP.txt"

        sudo bash -c "cat > $SECRET_FILE" <<EOF
# Grading App Secrets
# Generated: $(date)
#
# WARNING: Keep these secrets secure and never commit to version control

SECRET_KEY=$SECRET_KEY
DB_ENCRYPTION_KEY=$DB_ENCRYPTION_KEY
EOF

        sudo chmod 400 "$SECRET_FILE"  # Read-only for root

        echo -e "${GREEN}✓ Secrets saved to $SECRET_FILE${NC}"
        echo -e "${GREEN}✓ Permissions set to 400 (read-only for owner)${NC}"
        echo ""

        # Save encryption key separately
        sudo bash -c "echo '$DB_ENCRYPTION_KEY' > $SECURE_DIR/encryption.key"
        sudo chmod 400 "$SECURE_DIR/encryption.key"

        echo -e "${GREEN}✓ Encryption key also saved to $SECURE_DIR/encryption.key${NC}"
        echo ""
    fi
}

# Function to display security instructions
display_security_instructions() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}  Security Instructions${NC}"
    echo -e "${BLUE}================================${NC}"
    echo ""

    echo -e "${YELLOW}IMPORTANT SECURITY PRACTICES:${NC}"
    echo ""
    echo "1. ${GREEN}NEVER${NC} commit secrets to version control"
    echo "   - Add .env to .gitignore"
    echo "   - Use environment variables in production"
    echo ""

    echo "2. ${GREEN}BACKUP${NC} secrets to secure location"
    echo "   - Store offline backup of DB_ENCRYPTION_KEY"
    echo "   - Without encryption key, encrypted data is UNRECOVERABLE"
    echo ""

    echo "3. ${GREEN}ROTATE${NC} secrets regularly"
    echo "   - SECRET_KEY: Rotate every 90 days (invalidates sessions)"
    echo "   - DB_ENCRYPTION_KEY: Only rotate if compromised (requires re-encryption)"
    echo ""

    echo "4. ${GREEN}PRODUCTION${NC} deployment"
    echo "   - Set FLASK_ENV=production"
    echo "   - Use secrets manager (AWS Secrets Manager, HashiCorp Vault, etc.)"
    echo "   - Enable HTTPS (required for secure cookies)"
    echo ""

    echo "5. ${GREEN}PERMISSIONS${NC}"
    echo "   - .env file: chmod 600 (owner read/write only)"
    echo "   - Backup files: chmod 400 (owner read only)"
    echo "   - Secure directory: chmod 700 (owner full access only)"
    echo ""
}

# Function to test secrets
test_secrets() {
    echo -e "${YELLOW}Test secrets? (y/N):${NC} "
    read -r response

    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo -e "${YELLOW}Testing secrets...${NC}"

        # Test SECRET_KEY
        python3 <<EOF
import sys
secret_key = "$SECRET_KEY"

if len(secret_key) < 32:
    print("ERROR: SECRET_KEY too short")
    sys.exit(1)

print("✓ SECRET_KEY valid")
EOF

        # Test DB_ENCRYPTION_KEY
        python3 <<EOF
from cryptography.fernet import Fernet
import sys

try:
    key = "$DB_ENCRYPTION_KEY"
    fernet = Fernet(key.encode())

    # Test encryption/decryption
    test_data = b"test message"
    encrypted = fernet.encrypt(test_data)
    decrypted = fernet.decrypt(encrypted)

    if decrypted != test_data:
        print("ERROR: Encryption test failed")
        sys.exit(1)

    print("✓ DB_ENCRYPTION_KEY valid and functional")
except Exception as e:
    print(f"ERROR: DB_ENCRYPTION_KEY test failed: {e}")
    sys.exit(1)
EOF

        echo -e "${GREEN}✓ All secrets validated${NC}"
        echo ""
    fi
}

# Main execution
main() {
    # Check dependencies
    if ! command -v python3 &> /dev/null; then
        echo -e "${RED}ERROR: python3 is required but not installed${NC}"
        exit 1
    fi

    # Check for cryptography package
    if ! python3 -c "import cryptography" 2>/dev/null; then
        echo -e "${RED}ERROR: Python cryptography package is required${NC}"
        echo "Install with: pip install cryptography"
        exit 1
    fi

    # Generate secrets
    generate_secret_key
    generate_encryption_key

    # Validate
    validate_secret_strength "$SECRET_KEY" "SECRET_KEY"
    validate_secret_strength "$DB_ENCRYPTION_KEY" "DB_ENCRYPTION_KEY"

    echo ""

    # Display
    display_secrets

    # Test
    test_secrets

    # Save options
    save_to_env
    save_to_secure_location

    # Instructions
    display_security_instructions

    echo -e "${GREEN}================================${NC}"
    echo -e "${GREEN}  Secrets generation complete!${NC}"
    echo -e "${GREEN}================================${NC}"
}

# Run main function
main

# Exit successfully
exit 0
