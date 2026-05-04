import os

import psycopg2

DB_HOST = os.environ.get("PG_HOST", "192.168.4.32")
DB_PASS = os.environ["PG_PASSWORD"]


def run_migration():
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(
            dbname="postgres",
            user="postgres",
            password=DB_PASS,
            host=DB_HOST,
            port="5432",
        )
        conn.autocommit = False
        cursor = conn.cursor()

        print("=" * 50)
        print("Starting DB Migration")
        print("=" * 50)

        # STEP 1  Remove duplicate rows from Activity_Timeline
        print("\n[1/6] Removing duplicate Activity_Timeline rows...")
        cursor.execute("""
            DELETE FROM Activity_Timeline a
            USING Activity_Timeline b
            WHERE a.id > b.id
              AND a.steam_id = b.steam_id
              AND a.app_id   = b.app_id
              AND a.achievement_timestamp = b.achievement_timestamp;
        """)
        deleted = cursor.rowcount
        print(f"      Deleted {deleted} duplicate row(s).")

        # STEP 2 Add UNIQUE constraint to Activity_Timeline
        print("\n[2/6] Adding UNIQUE constraint to Activity_Timeline...")
        cursor.execute("""
            DO $$
            BEGIN
                IF NOT EXISTS (
                    SELECT 1 FROM pg_constraint
                    WHERE conname = 'uq_timeline'
                ) THEN
                    ALTER TABLE Activity_Timeline
                    ADD CONSTRAINT uq_timeline
                    UNIQUE (steam_id, app_id, achievement_timestamp);
                    RAISE NOTICE 'Constraint uq_timeline added.';
                ELSE
                    RAISE NOTICE 'Constraint uq_timeline already exists, skipping.';
                END IF;
            END $$;
        """)
        print("      Done.")

        # STEP 3  Add total_games_owned column to Users
        print("\n[3/6] Adding total_games_owned column to Users...")
        cursor.execute("""
            ALTER TABLE Users
            ADD COLUMN IF NOT EXISTS total_games_owned INT;
        """)
        print("      Done.")

        # STEP 4 — Add missing indexes
        print("\n[4/6] Adding missing indexes...")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_library_steam
            ON User_Library(steam_id);
        """)
        print("      idx_library_steam — OK")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_steam_app
            ON Activity_Timeline(steam_id, app_id);
        """)
        print("      idx_timeline_steam_app — OK")

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timeline_timestamp
            ON Activity_Timeline(achievement_timestamp);
        """)
        print("      idx_timeline_timestamp — OK (already existed or created now)")

        # STEP 5  Verify row counts so you can sanity-check after migration
        print("\n[5/6] Row count check...")
        for table in ["Users", "Games", "User_Library", "Activity_Timeline"]:
            cursor.execute(f"SELECT COUNT(*) FROM {table};")
            count = cursor.fetchone()[0]
            print(f"      {table}: {count:,} rows")

        # STEP 6  Commit everything
        print("\n[6/6] Committing migration...")
        conn.commit()
        print("\n Migration complete. No data was lost.")
        print("   Next step: run backfill_existing_users() to patch your 20k users.")

    except Exception as e:
        print(f"\n Migration failed: {e}")
        print("   Rolling back — your database is unchanged.")
        if conn:
            conn.rollback()
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


if __name__ == "__main__":
    run_migration()
