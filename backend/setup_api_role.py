"""Provision the local API reader and append-only investigator; never print passwords."""
import json
import os

from psycopg import sql

from database import database_engine


def setup_reader() -> None:
    password = os.environ["DB_PASSWORD"]
    if len(password) < 24:
        raise ValueError("API database password must contain at least 24 characters")
    engine = database_engine()
    try:
        with engine.begin() as connection:
            cursor = connection.connection.driver_connection.cursor()
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aegis_api'")
            if cursor.fetchone() is None:
                cursor.execute("CREATE ROLE aegis_api")
            cursor.execute(sql.SQL(
                "ALTER ROLE aegis_api WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Literal(password)))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO aegis_api").format(
                sql.Identifier(os.getenv("DB_NAME", "aegisops")),
            ))
            cursor.execute("GRANT USAGE ON SCHEMA public TO aegis_api")
            cursor.execute("REVOKE ALL ON TABLE public.incident_events FROM aegis_api")
            cursor.execute("GRANT SELECT ON TABLE public.incident_events TO aegis_api")
            cursor.execute("REVOKE ALL ON TABLE public.investigation_runs FROM aegis_api")
            cursor.execute("GRANT SELECT ON TABLE public.investigation_runs TO aegis_api")
            writer_password = os.environ["INVESTIGATOR_PASSWORD"]
            if len(writer_password) < 24:
                raise ValueError("Investigator password must contain at least 24 characters")
            cursor.execute("SELECT 1 FROM pg_roles WHERE rolname = 'aegis_investigator'")
            if cursor.fetchone() is None:
                cursor.execute("CREATE ROLE aegis_investigator")
            cursor.execute(sql.SQL(
                "ALTER ROLE aegis_investigator WITH LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}"
            ).format(sql.Literal(writer_password)))
            cursor.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO aegis_investigator").format(
                sql.Identifier(os.getenv("DB_NAME", "aegisops"))))
            cursor.execute("GRANT USAGE ON SCHEMA public TO aegis_investigator")
            cursor.execute("REVOKE ALL ON TABLE public.incident_events, public.investigation_runs FROM aegis_investigator")
            cursor.execute("GRANT SELECT ON TABLE public.incident_events TO aegis_investigator")
            cursor.execute("GRANT SELECT, INSERT ON TABLE public.investigation_runs TO aegis_investigator")
            cursor.execute("ALTER ROLE aegis_investigator SET search_path = public")
            cursor.execute("ALTER ROLE aegis_api SET default_transaction_read_only = on")
            cursor.execute("ALTER ROLE aegis_api SET search_path = public")
            cursor.close()
        print(json.dumps({"event": "api_reader_configured", "role": "aegis_api"}))
    finally:
        engine.dispose()


if __name__ == "__main__":
    try:
        setup_reader()
    except Exception as error:
        # Do not expose credential-bearing SQL in provisioning tracebacks.
        print(json.dumps({"event": "api_reader_setup_failed", "reason": type(error).__name__}))
        raise SystemExit(1) from None
