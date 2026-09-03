#!/usr/bin/env bash
# Obtain a Cognito refresh token for the Veolia integration.
#
# Run this from a machine you usually browse the portal from: Cognito's
# adaptive authentication asks for no verification code there, while it does
# from a server whose context it does not recognise.
#
# The token is printed so it can be pasted into Home Assistant. It is a
# credential in its own right -- do not share it. It carries its own validity,
# sometimes as short as one hour, and serves to get an address accepted by
# Veolia rather than to replace the password for good.
set -u

# National portal by default. For another portal, take the client id from the
# VEOLIA_PORTALS table in veolia_api/portals.py, for instance:
#   VEOLIA_CLIENT_ID=19bjc8ldefie683n889iiubjc8   Eau de Toulouse Metropole
#   VEOLIA_CLIENT_ID=54e8dri103e65defj6p67eolli   Eau de Perpignan Mediterranee
CLIENT_ID="${VEOLIA_CLIENT_ID:-3kghade1fg54739kj8pkbova8j}"

printf 'Veolia e-mail: '
IFS= read -r VEOLIA_USER
printf 'Password: '
stty -echo; IFS= read -r VEOLIA_PASS; stty echo; printf '\n'

if [ -z "$VEOLIA_USER" ] || [ -z "$VEOLIA_PASS" ]; then
  echo "Empty input: nothing was sent." >&2
  exit 1
fi

# Credentials travel through stdin, never through the environment: an exported
# variable would be readable in /proc/<pid>/environ by any task of the same
# user.
printf '%s\n%s\n' "$VEOLIA_USER" "$VEOLIA_PASS" | CLIENT_ID="$CLIENT_ID" python3 -c '
import json, os, sys, urllib.error, urllib.request

user = sys.stdin.readline().rstrip("\n")
password = sys.stdin.readline().rstrip("\n")

request = urllib.request.Request(
    "https://cognito-idp.eu-west-3.amazonaws.com/",
    data=json.dumps({
        "ClientId": os.environ["CLIENT_ID"],
        "AuthFlow": "USER_PASSWORD_AUTH",
        "AuthParameters": {"USERNAME": user, "PASSWORD": password},
    }).encode(),
    headers={
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
    },
)
try:
    with urllib.request.urlopen(request, timeout=20) as response:
        body = json.load(response)
except urllib.error.HTTPError as err:
    body = json.load(err)

if challenge := body.get("ChallengeName"):
    print(f"\nCognito demanded the {challenge} challenge from this machine.",
          file=sys.stderr)
    print("Run this again from the machine you usually browse the portal from.",
          file=sys.stderr)
    raise SystemExit(1)

token = (body.get("AuthenticationResult") or {}).get("RefreshToken")
if not token:
    print(f"\nUnexpected response (keys: {sorted(body)})", file=sys.stderr)
    raise SystemExit(1)

print("\n=== Refresh token -- paste this into Home Assistant ===\n")
print(token)
'

unset VEOLIA_USER VEOLIA_PASS
