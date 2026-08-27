import hashlib
import sqlite3
import uuid
from pathlib import Path

DB_PATH = Path('./data/db.sqlite3')
MIGRATIONS_DIR = Path('./prisma/migrations')

# mirrors the table Prisma uses so an existing prisma-migrated database is read
# correctly and never re-applied
MIGRATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS "_prisma_migrations" (
    "id" TEXT PRIMARY KEY NOT NULL,
    "checksum" TEXT NOT NULL,
    "finished_at" DATETIME,
    "migration_name" TEXT NOT NULL,
    "logs" TEXT,
    "rolled_back_at" DATETIME,
    "started_at" DATETIME NOT NULL DEFAULT current_timestamp,
    "applied_steps_count" INTEGER UNSIGNED NOT NULL DEFAULT 0
);
"""


def pending(conn: sqlite3.Connection) -> list[Path]:
    applied = {row[0] for row in
               conn.execute('SELECT migration_name FROM "_prisma_migrations"')}
    migrations = [d for d in MIGRATIONS_DIR.iterdir()
                  if d.is_dir() and (d / 'migration.sql').exists()]
    return sorted((m for m in migrations if m.name not in applied),
                  key=lambda m: m.name)


def run() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(MIGRATIONS_TABLE)
        for migration in pending(conn):
            sql = (migration / 'migration.sql').read_text()
            conn.executescript(sql)
            conn.execute(
                'INSERT INTO "_prisma_migrations" (id, checksum, '
                'migration_name, finished_at, applied_steps_count) '
                'VALUES (?, ?, ?, current_timestamp, 1)',
                (str(uuid.uuid4()),
                 hashlib.sha256(sql.encode()).hexdigest(),
                 migration.name))
            conn.commit()
            print(f'Applied migration {migration.name}')
    finally:
        conn.close()


if __name__ == '__main__':
    run()
