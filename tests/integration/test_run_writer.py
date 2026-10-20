"""Use investigator credentials; all test inserts are rolled back."""
import unittest
from unittest.mock import Mock

from sqlalchemy import text
from sqlalchemy.exc import DBAPIError, IntegrityError

from database import database_engine
from event_repository import EventRepository
from investigator import run_investigation
from investigator_cli import load_event
from run_repository import assert_investigator_role, save_run


class RunWriterTests(unittest.TestCase):
    def setUp(self):
        self.engine = database_engine("INVESTIGATOR_PASSWORD")

    def tearDown(self):
        self.engine.dispose()

    def test_save_and_read_round_trip_and_duplicate_rejection(self):
        assert_investigator_role(self.engine)
        event = load_event(EventRepository(self.engine), None)
        report = run_investigation(event)
        with self.engine.connect() as connection:
            transaction = connection.begin()
            try:
                # Exercise the actual repository through SAVEPOINTs under a rolled-back outer transaction.
                proxy = Mock()
                proxy.begin.side_effect = lambda: SavepointConnection(connection)
                save_run(proxy, report)
                row = connection.execute(text("SELECT payload FROM investigation_runs WHERE run_id=:id"),
                                         {"id": report["run_id"]}).scalar_one()
                self.assertEqual(row, report)
                with self.assertRaises(IntegrityError):
                    save_run(proxy, report)
            finally:
                transaction.rollback()

    def test_writer_cannot_mutate_events_or_existing_runs(self):
        for statement in ["DELETE FROM incident_events WHERE false",
                          "UPDATE incident_events SET source=source WHERE false",
                          "DELETE FROM investigation_runs WHERE false",
                          "UPDATE investigation_runs SET state=state WHERE false"]:
            with self.subTest(statement=statement), self.engine.connect() as connection:
                transaction = connection.begin()
                try:
                    with self.assertRaises(DBAPIError) as error:
                        connection.execute(text(statement))
                    self.assertEqual(error.exception.orig.sqlstate, "42501")
                finally:
                    transaction.rollback()

    def test_foreign_key_rejects_missing_source_event(self):
        event = load_event(EventRepository(self.engine), None)
        report = run_investigation(event)
        report["event_id"] = "0" * 64
        with self.engine.connect() as connection:
            transaction = connection.begin()
            try:
                proxy = Mock()
                proxy.begin.side_effect = lambda: SavepointConnection(connection)
                with self.assertRaises(IntegrityError) as error:
                    save_run(proxy, report)
                self.assertEqual(error.exception.orig.sqlstate, "23503")
            finally:
                transaction.rollback()


class SavepointConnection:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.savepoint = self.connection.begin_nested()
        return self.connection

    def __exit__(self, *args):
        return self.savepoint.__exit__(*args)
