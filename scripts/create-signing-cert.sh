#!/bin/bash
# Create a self-signed code-signing identity for rmcd in the login keychain.
#
# Ad-hoc signed builds are identified by macOS privacy controls (TCC) by
# their code hash, so every rebuild looks like a new app and loses its
# Apple Music / Automation permissions. Signing with a stable certificate
# makes TCC match on certificate + bundle ID instead, so permissions granted
# once survive rebuilds. Idempotent: re-running only repairs codesign's
# access to an existing identity if needed.

set -euo pipefail

NAME="${RMCD_SIGNING_IDENTITY:-rmcd Local Code Signing}"
KEYCHAIN="$HOME/Library/Keychains/login.keychain-db"
# Apple's LibreSSL writes PKCS#12 files that `security import` accepts.
OPENSSL=/usr/bin/openssl

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

can_sign() {
    cp /usr/bin/true "$TMP/probe"
    codesign --force --sign "$NAME" "$TMP/probe" > /dev/null 2>&1
}

# Keys imported from the command line also need Apple's tools added to their
# partition list, or codesign fails with errSecInternalComponent. This asks
# for the login keychain password.
authorise_codesign() {
    echo "Authorising codesign to use the key (enter your login password):"
    security set-key-partition-list -S apple-tool:,apple: -s -l "$NAME" "$KEYCHAIN" > /dev/null
}

if security find-certificate -c "$NAME" "$KEYCHAIN" > /dev/null 2>&1; then
    if can_sign; then
        echo "Signing identity '$NAME' already exists and is usable"
        exit 0
    fi
    authorise_codesign
    can_sign && echo "Signing identity '$NAME' is now usable" && exit 0
    echo "codesign still cannot use '$NAME' (is the login keychain unlocked?)" >&2
    exit 1
fi

cat > "$TMP/cert.cnf" <<EOF
[req]
distinguished_name = dn
x509_extensions = ext
prompt = no
[dn]
CN = $NAME
[ext]
basicConstraints = critical, CA:false
keyUsage = critical, digitalSignature
extendedKeyUsage = critical, codeSigning
EOF

"$OPENSSL" req -x509 -newkey rsa:2048 -nodes -days 3650 \
    -config "$TMP/cert.cnf" -keyout "$TMP/key.pem" -out "$TMP/cert.pem" 2> /dev/null

PASS="$(uuidgen)"
"$OPENSSL" pkcs12 -export -inkey "$TMP/key.pem" -in "$TMP/cert.pem" \
    -name "$NAME" -out "$TMP/identity.p12" -passout "pass:$PASS"

# -T lets codesign use the key without a keychain prompt on every build.
security import "$TMP/identity.p12" -k "$KEYCHAIN" -P "$PASS" -T /usr/bin/codesign
authorise_codesign

echo "Created signing identity '$NAME'"
