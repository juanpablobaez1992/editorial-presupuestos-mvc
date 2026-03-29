from __future__ import annotations

import base64
import sys

from pwdlib import PasswordHash


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python scripts/generar_password_hash.py "TuPasswordSegura"')

    password = sys.argv[1]
    if len(password) < 12:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres.")

    password_hasher = PasswordHash.recommended()
    password_hash = password_hasher.hash(password)
    password_hash_b64 = base64.b64encode(password_hash.encode("utf-8")).decode("utf-8")

    print("HASH=" + password_hash)
    print("HASH_B64=" + password_hash_b64)


if __name__ == "__main__":
    main()
