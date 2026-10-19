#!/usr/bin/env bash
# Creates the three runtime roles + the SECURITY DEFINER owner role.
# Runs once, on first container start, as the Postgres superuser.
# Passwords come from the environment (see .env.example). Dev defaults only.
set -euo pipefail

: "${TRIAVOZ_OWNER_PASSWORD:?missing}"
: "${TRIAVOZ_APP_PASSWORD:?missing}"
: "${TRIAVOZ_OPS_PASSWORD:?missing}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
  -- Owner of the schema: used ONLY by migrations (never at runtime).
  CREATE ROLE triavoz_owner LOGIN PASSWORD '${TRIAVOZ_OWNER_PASSWORD}' NOSUPERUSER NOBYPASSRLS;

  -- Runtime role used by the API. No superuser, no BYPASSRLS, not the table owner.
  CREATE ROLE triavoz_app LOGIN PASSWORD '${TRIAVOZ_APP_PASSWORD}' NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE;

  -- Global, audited role for internal jobs (retention purge, aggregate metrics).
  -- NEVER used on any customer-request code path.
  CREATE ROLE triavoz_ops LOGIN PASSWORD '${TRIAVOZ_OPS_PASSWORD}' NOSUPERUSER NOBYPASSRLS;

  -- Owns the few SECURITY DEFINER routing functions. NOLOGIN, BYPASSRLS, tiny grants.
  CREATE ROLE triavoz_definer NOLOGIN NOSUPERUSER BYPASSRLS;

  -- Lets migrations (triavoz_owner) assign SECURITY DEFINER functions to triavoz_definer.
  GRANT triavoz_definer TO triavoz_owner;

  ALTER DATABASE "$POSTGRES_DB" OWNER TO triavoz_owner;
  \connect "$POSTGRES_DB"
  CREATE EXTENSION IF NOT EXISTS pgcrypto;
  CREATE EXTENSION IF NOT EXISTS btree_gist;
  CREATE EXTENSION IF NOT EXISTS citext;
  ALTER SCHEMA public OWNER TO triavoz_owner;
  REVOKE ALL ON SCHEMA public FROM PUBLIC;
  GRANT USAGE ON SCHEMA public TO triavoz_app, triavoz_ops, triavoz_definer;
EOSQL
