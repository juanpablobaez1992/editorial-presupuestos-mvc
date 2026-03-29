from __future__ import annotations

import sys

from pwdlib import PasswordHash


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit('Uso: python scripts/generar_password_hash.py "TuPasswordSegura"')

    password = sys.argv[1]
    if len(password) < 12:
        raise SystemExit("La contraseña debe tener al menos 12 caracteres.")

    password_hasher = PasswordHash.recommended()
    print(password_hasher.hash(password))


if __name__ == "__main__":
    main()
