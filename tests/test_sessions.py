import unittest

from dbeeapp.errors import ConnectionLostError
from dbeeapp.sessions import SessionManager


class FakeConnection:
    def __init__(self, name, fail_close=False):
        self.name = name
        self.closed = False
        self.fail_close = fail_close

    def close(self):
        self.closed = True
        if self.fail_close:
            raise RuntimeError("close failure")


class SessionManagerTests(unittest.TestCase):
    def setUp(self):
        self.databases = {
            "control": {"user": "u", "credential": {"provider": "dummy", "options": {}}},
            "reporting": {"user": "u", "credential": {"provider": "dummy", "options": {}}},
        }
        self.config = {"provider_dir": "/providers", "timeouts": {"provider": 1}}
        self.config["providers"] = {"dummy": {"default_region": "dev", "password": "default"}}
        self.opened = []
        self.provider_calls = []

        def provider(*args):
            self.provider_calls.append(args)
            return "not-exposed"

        def connector(database, password, config):
            connection = FakeConnection("conn-{}".format(len(self.opened)))
            self.opened.append(connection)
            return connection

        self.manager = SessionManager(self.databases, self.config, connector=connector, provider=provider)

    def test_reuses_sessions_when_switching_databases(self):
        with self.manager.session("control") as control_one:
            pass
        with self.manager.session("reporting") as reporting_one:
            pass
        with self.manager.session("control") as control_two:
            pass
        with self.manager.session("reporting") as reporting_two:
            pass
        self.assertIs(control_one, control_two)
        self.assertIs(reporting_one, reporting_two)
        self.assertEqual(len(self.opened), 2)
        self.assertEqual(len(self.provider_calls), 2)

    def test_provider_options_merge_app_defaults_then_database_overrides(self):
        self.databases["control"]["credential"]["options"] = {"password": "job-test-only", "safe": "DB_TEST"}
        with self.manager.session("control"):
            pass
        provider_options = self.provider_calls[0][3]
        self.assertEqual(provider_options, {"default_region": "dev", "password": "job-test-only", "safe": "DB_TEST"})

    def test_new_and_override_close_without_replacing_reusable(self):
        with self.manager.session("control") as original:
            pass
        with self.manager.session("control", mode="new") as temporary:
            self.assertIsNot(original, temporary)
            self.assertFalse(temporary.closed)
        self.assertTrue(temporary.closed)
        with self.manager.session("control") as resumed:
            self.assertIs(original, resumed)
        self.assertEqual(len(self.opened), 2)

    def test_all_connections_close_even_when_one_close_fails(self):
        with self.manager.session("control"):
            pass
        with self.manager.session("reporting"):
            pass
        self.opened[0].fail_close = True
        self.manager.close_all()
        self.assertTrue(all(connection.closed for connection in self.opened))
        self.assertEqual(self.manager.reusable, {})

    def test_lost_session_is_not_silently_reopened(self):
        with self.assertRaises(ConnectionLostError):
            with self.manager.session("control"):
                raise ConnectionLostError("lost")
        self.assertTrue(self.opened[0].closed)
        with self.assertRaises(ConnectionLostError):
            with self.manager.session("control"):
                pass
        self.assertEqual(len(self.opened), 1)


if __name__ == "__main__":
    unittest.main()