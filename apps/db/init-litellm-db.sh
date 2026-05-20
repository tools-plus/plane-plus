#!/bin/bash
# Create the litellm database for LiteLLM's Prisma ORM on first postgres init
set -e
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    SELECT 'CREATE DATABASE litellm'
    WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'litellm')\gexec
EOSQL
