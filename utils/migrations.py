from __future__ import annotations

import logging

from utils.config import PRIMARY_OWNER_ID
from utils.database import connect, execute_many

log = logging.getLogger(__name__)


async def run_startup_migrations() -> None:
    """Create missing tables and enforce the single-owner no-prefix policy."""
    await execute_many(
        "prefix.db",
        [
            """
            CREATE TABLE IF NOT EXISTS prefixes (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT NOT NULL
            )
            """,
        ],
    )

    await execute_many(
        "np.db",
        [
            """
            CREATE TABLE IF NOT EXISTS np (
                id INTEGER PRIMARY KEY,
                expiry_time TEXT NULL
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS staff (
                id INTEGER PRIMARY KEY
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS autonp (
                guild_id INTEGER PRIMARY KEY
            )
            """,
        ],
    )

    async with connect("np.db") as db:
        async with db.execute("PRAGMA table_info(np)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}
        if "expiry_time" not in columns:
            await db.execute("ALTER TABLE np ADD COLUMN expiry_time TEXT NULL")
        cursor = await db.execute("DELETE FROM np WHERE id != ?", (PRIMARY_OWNER_ID,))
        removed_no_prefix_users = cursor.rowcount
        await db.commit()
    if removed_no_prefix_users:
        log.info(
            "Removed %s non-owner entries from the no-prefix list.",
            removed_no_prefix_users,
        )

    await execute_many(
        "block.db",
        [
            """
            CREATE TABLE IF NOT EXISTS user_blacklist (
                user_id TEXT PRIMARY KEY,
                timestamp TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS guild_blacklist (
                guild_id TEXT PRIMARY KEY,
                timestamp TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER
            )
            """,
        ],
    )

    await execute_many(
        "ignore.db",
        [
            "CREATE TABLE IF NOT EXISTS ignored_commands (guild_id INTEGER, command_name TEXT)",
            "CREATE TABLE IF NOT EXISTS ignored_channels (guild_id INTEGER, channel_id INTEGER)",
            "CREATE TABLE IF NOT EXISTS ignored_users (guild_id INTEGER, user_id INTEGER)",
            "CREATE TABLE IF NOT EXISTS bypassed_users (guild_id INTEGER, user_id INTEGER)",
        ],
    )

    await execute_many(
        "topcheck.db",
        [
            """
            CREATE TABLE IF NOT EXISTS topcheck (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0
            )
            """,
        ],
    )

    await execute_many(
        "automod.db",
        [
            """
            CREATE TABLE IF NOT EXISTS automod (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS automod_punishments (
                guild_id INTEGER,
                event TEXT,
                punishment TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS automod_ignored (
                guild_id INTEGER,
                type TEXT,
                id INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS automod_logging (
                guild_id INTEGER PRIMARY KEY,
                log_channel INTEGER
            )
            """,
        ],
    )

    await execute_many(
        "emoji_sync.db",
        [
            """
            CREATE TABLE IF NOT EXISTS emoji_sync_settings (
                guild_id INTEGER PRIMARY KEY,
                auto_sync INTEGER NOT NULL DEFAULT 0,
                sync_to_application INTEGER NOT NULL DEFAULT 0,
                updated_at TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS emoji_sync_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER,
                status TEXT NOT NULL,
                uploaded INTEGER NOT NULL DEFAULT 0,
                skipped INTEGER NOT NULL DEFAULT 0,
                failed INTEGER NOT NULL DEFAULT 0,
                details TEXT,
                created_at TEXT NOT NULL
            )
            """,
        ],
    )

    await execute_many(
        "anti.db",
        [
            """
            CREATE TABLE IF NOT EXISTS antinuke (
                guild_id INTEGER PRIMARY KEY,
                status BOOLEAN NOT NULL DEFAULT 0
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS extraowners (
                guild_id INTEGER,
                owner_id INTEGER,
                PRIMARY KEY (guild_id, owner_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS whitelisted_users (
                guild_id INTEGER,
                user_id INTEGER,
                ban BOOLEAN DEFAULT 0,
                kick BOOLEAN DEFAULT 0,
                prune BOOLEAN DEFAULT 0,
                botadd BOOLEAN DEFAULT 0,
                serverup BOOLEAN DEFAULT 0,
                memup BOOLEAN DEFAULT 0,
                chcr BOOLEAN DEFAULT 0,
                chdl BOOLEAN DEFAULT 0,
                chup BOOLEAN DEFAULT 0,
                rlcr BOOLEAN DEFAULT 0,
                rlup BOOLEAN DEFAULT 0,
                rldl BOOLEAN DEFAULT 0,
                meneve BOOLEAN DEFAULT 0,
                mngweb BOOLEAN DEFAULT 0,
                mngstemo BOOLEAN DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS limit_settings (
                guild_id INTEGER,
                action_type TEXT,
                action_limit INTEGER,
                time_window INTEGER,
                PRIMARY KEY (guild_id, action_type)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS Nightmode (
                guildId TEXT,
                roleId TEXT,
                adminPermissions INTEGER
            )
            """,
        ],
    )

    await execute_many(
        "warn.db",
        [
            """
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                moderator_id INTEGER NOT NULL,
                reason TEXT,
                timestamp TEXT NOT NULL
            )
            """,
        ],
    )

    await execute_many(
        "afk.db",
        [
            """
            CREATE TABLE IF NOT EXISTS afk (
                user_id INTEGER PRIMARY KEY,
                AFK TEXT NOT NULL DEFAULT 'False',
                reason TEXT NOT NULL DEFAULT 'None',
                time INTEGER NOT NULL DEFAULT 0,
                mentions INTEGER NOT NULL DEFAULT 0,
                dm TEXT NOT NULL DEFAULT 'False'
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS afk_guild (
                user_id INTEGER NOT NULL,
                guild_id INTEGER NOT NULL,
                PRIMARY KEY (user_id, guild_id)
            )
            """,
        ],
    )

    async with connect("afk.db") as db:
        async with db.execute("PRAGMA table_info(afk)") as cursor:
            columns = {row[1] for row in await cursor.fetchall()}

        if columns and "AFK" not in columns:
            log.info("Upgrading afk.db schema to the current AFK table layout.")
            await db.execute(
                """
                CREATE TABLE IF NOT EXISTS afk_new (
                    user_id INTEGER PRIMARY KEY,
                    AFK TEXT NOT NULL DEFAULT 'False',
                    reason TEXT NOT NULL DEFAULT 'None',
                    time INTEGER NOT NULL DEFAULT 0,
                    mentions INTEGER NOT NULL DEFAULT 0,
                    dm TEXT NOT NULL DEFAULT 'False'
                )
                """
            )
            if "since" in columns:
                await db.execute(
                    """
                    INSERT INTO afk_new (user_id, reason, time)
                    SELECT user_id,
                           COALESCE(reason, 'None'),
                           CASE
                               WHEN since GLOB '[0-9]*' THEN CAST(since AS INTEGER)
                               ELSE 0
                           END
                    FROM afk
                    """
                )
            elif "user_id" in columns:
                await db.execute(
                    """
                    INSERT INTO afk_new (user_id, reason)
                    SELECT user_id, COALESCE(reason, 'None')
                    FROM afk
                    """
                )
            await db.execute("DROP TABLE afk")
            await db.execute("ALTER TABLE afk_new RENAME TO afk")
            await db.commit()
            log.info("afk.db schema upgrade complete.")

    await execute_many(
        "giveaways.db",
        [
            """
            CREATE TABLE IF NOT EXISTS Giveaway (
                guild_id INTEGER,
                host_id INTEGER,
                start_time TIMESTAMP,
                ends_at TIMESTAMP,
                prize TEXT,
                winners INTEGER,
                message_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, message_id)
            )
            """,
        ],
    )

    await execute_many(
        "blword.db",
        [
            """
            CREATE TABLE IF NOT EXISTS blacklist (
                guild_id TEXT,
                word TEXT,
                PRIMARY KEY (guild_id, word)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bypass (
                guild_id TEXT,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS bypass_roles (
                guild_id TEXT,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
            """,
        ],
    )

    await execute_many(
        "logging.db",
        [
            """
            CREATE TABLE IF NOT EXISTS log_channels (
                guild_id INTEGER,
                log_type TEXT,
                channel_id INTEGER
            )
            """,
        ],
    )

    await execute_many(
        "fastgreet.db",
        [
            """
            CREATE TABLE IF NOT EXISTS greet_channels (
                guild_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, channel_id)
            )
            """,
        ],
    )

    await execute_many(
        "messages.db",
        [
            """
            CREATE TABLE IF NOT EXISTS messages (
                guild_id INTEGER,
                user_id INTEGER,
                date TEXT,
                count INTEGER
            )
            """,
        ],
    )

    await execute_many(
        "jail.db",
        [
            """
            CREATE TABLE IF NOT EXISTS jailed (
                guild_id TEXT,
                user_id TEXT,
                mod_id TEXT,
                reason TEXT,
                jailed_at TEXT,
                duration INTEGER,
                roles TEXT,
                PRIMARY KEY (guild_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS jail_settings (
                guild_id TEXT PRIMARY KEY,
                jail_role TEXT,
                jail_channel TEXT,
                mod_role TEXT,
                log_channel TEXT
            )
            """,
        ],
    )

    await execute_many(
        "vanity.db",
        [
            """
            CREATE TABLE IF NOT EXISTS vanity_roles (
                guild_id INTEGER,
                vanity TEXT NOT NULL,
                role_id INTEGER NOT NULL,
                log_channel_id INTEGER NOT NULL,
                current_status TEXT,
                PRIMARY KEY (guild_id, vanity)
            )
            """,
        ],
    )

    await execute_many(
        "invite_tracker.db",
        [
            """
            CREATE TABLE IF NOT EXISTS invites (
                guild_id TEXT,
                inviter_id TEXT,
                invite_code TEXT,
                uses INTEGER DEFAULT 0,
                PRIMARY KEY(guild_id, invite_code)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS invite_stats (
                guild_id TEXT,
                user_id TEXT,
                invites INTEGER DEFAULT 0,
                fake INTEGER DEFAULT 0,
                leaves INTEGER DEFAULT 0,
                rejoins INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS invite_settings (
                guild_id TEXT PRIMARY KEY,
                enabled INTEGER DEFAULT 0
            )
            """,
        ],
    )

    await execute_many(
        "rr.db",
        [
            """
            CREATE TABLE IF NOT EXISTS reaction_roles (
                guild_id INTEGER,
                message_id INTEGER,
                emoji TEXT,
                role_id INTEGER
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS rr_settings (
                guild_id INTEGER PRIMARY KEY,
                dm_enabled INTEGER DEFAULT 1
            )
            """,
        ],
    )

    log.info("Startup database migrations completed.")