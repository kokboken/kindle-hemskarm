"""Sparar Västtrafik-nycklarna i .env och testar dem direkt.

Kör:  .\\.venv\\Scripts\\python scripts\\vt_keys.py
Nycklarna visas inte på skärmen.
"""
import getpass
import os
import re
import sys

import requests

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV = os.path.join(ROOT, ".env")


def set_value(text, key, value):
    if re.search(rf"^{key}=.*$", text, re.M):
        return re.sub(rf"^{key}=.*$", lambda _: f"{key}={value}", text, flags=re.M)
    return text + f"\n{key}={value}\n"


def main():
    print("Hittas på developer.vasttrafik.se under din applikation.")
    cid = getpass.getpass("Klistra in Client ID (syns inte) och tryck Enter: ").strip()
    secret = getpass.getpass("Klistra in Client secret (syns inte) och tryck Enter: ").strip()
    if not cid or not secret:
        sys.exit("Något var tomt – avbryter.")

    print("Testar mot Västtrafik…")
    r = requests.post("https://ext-api.vasttrafik.se/token", data={"grant_type": "client_credentials"},
                      auth=(cid, secret), timeout=15)
    if r.status_code != 200:
        sys.exit(f"Västtrafik godtog inte nycklarna (HTTP {r.status_code}). Kontrollera dem och försök igen.")
    token = r.json()["access_token"]
    r = requests.get("https://ext-api.vasttrafik.se/pr/v4/locations/by-text",
                     params={"q": "Järntorget", "types": "stoparea", "limit": 1},
                     headers={"Authorization": f"Bearer {token}"}, timeout=15)
    if r.status_code != 200:
        sys.exit(f"Nycklarna fungerar, men Planera Resa v4 svarade HTTP {r.status_code}. "
                 "Kontrollera att appen prenumererar på Planera Resa v4.")
    print("Fungerar! Hittade:", (r.json().get("results") or [{}])[0].get("name", "?"))

    with open(ENV, encoding="utf-8-sig") as f:
        text = f.read()
    text = set_value(text, "VT_CLIENT_ID", cid)
    text = set_value(text, "VT_CLIENT_SECRET", secret)
    with open(ENV, "w", encoding="utf-8") as f:
        f.write(text)
    print("Sparat i .env. Klart!")


if __name__ == "__main__":
    main()
