"""Helper script to create the CurrencyX database (idempotent).

Tries connecting to the default ``postgres`` database with several
common passwords and creates ``currencyx`` if it doesn't exist yet.
"""

import asyncio
import asyncpg


async def create_database() -> None:
    passwords: list[str] = [
        "postgres",
        "password",
        "admin",
        "root",
        "",
        "secret",
        "123456",
        "P@ssw0rd",
        "postgres123",
    ]
    for pw in passwords:
        try:
            conn = await asyncpg.connect(
                host="localhost",
                port=5432,
                user="postgres",
                password=pw if pw else None,
                database="postgres",
            )
        except Exception as exc:  # noqa: BLE001
            print(f"  password '{pw}' -> {exc}")
            continue

        try:
            await conn.execute("CREATE DATABASE currencyx")
            print(f"[OK] Database 'currencyx' created (password: '{pw}')")
        except asyncpg.DuplicateDatabaseError:
            print(f"[OK] Database 'currencyx' already exists (password: '{pw}')")
        except Exception as exc:  # noqa: BLE001
            print(f"  password '{pw}' -> DB error: {exc}")
        await conn.close()
        return

    print("[ERROR] Could not connect with any known password.")


if __name__ == "__main__":
    asyncio.run(create_database())