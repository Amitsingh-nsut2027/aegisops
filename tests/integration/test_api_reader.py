"""Run with the API service credentials, never the migration administrator."""
import unittest

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from database import database_engine
from event_repository import EventRepository, assert_reader_role


class ApiReaderTests(unittest.TestCase):
    def setUp(self):
        self.engine = database_engine("DB_PASSWORD")

    def tearDown(self):
        self.engine.dispose()

    def test_role_can_read_events(self):
        assert_reader_role(self.engine)
        rows = EventRepository(self.engine).list_events(1, 0, "simulator")
        self.assertLessEqual(len(rows), 2)

    def test_write_denied_even_if_transaction_read_only_is_disabled(self):
        # WHERE false avoids data changes even if a permission regression occurs.
        with self.engine.connect() as connection:
            transaction = connection.begin()
            try:
                connection.execute(text("SET TRANSACTION READ WRITE"))
                with self.assertRaises(DBAPIError) as failure:
                    connection.execute(text("DELETE FROM public.incident_events WHERE false"))
                self.assertEqual(failure.exception.orig.sqlstate, "42501")
            finally:
                transaction.rollback()

    def test_cannot_create_tables_in_public_schema(self):
        with self.engine.connect() as connection:
            allowed = connection.execute(text(
                "SELECT has_schema_privilege(current_user, 'public', 'CREATE')"
            )).scalar_one()
        self.assertFalse(allowed)

    def test_investigation_history_is_read_only(self):
        from run_repository import RunRepository
        self.assertLessEqual(len(RunRepository(self.engine).list_runs(1, 0, None)), 2)
        for operation in ["DELETE FROM investigation_runs WHERE false",
                          "INSERT INTO investigation_runs SELECT * FROM investigation_runs WHERE false"]:
            with self.engine.connect() as connection:
                transaction = connection.begin()
                try:
                    connection.execute(text("SET TRANSACTION READ WRITE"))
                    with self.assertRaises(DBAPIError) as error:
                        connection.execute(text(operation))
                    self.assertEqual(error.exception.orig.sqlstate, "42501")
                finally:
                    transaction.rollback()


if __name__ == "__main__":
    unittest.main()
