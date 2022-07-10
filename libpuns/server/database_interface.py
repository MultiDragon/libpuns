import abc

from libpuns.connection.datagram_util import ObjectID


class DatabaseInterface(abc.ABC):
    @abc.abstractmethod
    def attempt_login(self, login: str, token: str) -> ObjectID | None:
        ...

    @abc.abstractmethod
    def update_object(self, oid: ObjectID, field: str, value):
        ...


class DummyDatabaseInterface(DatabaseInterface):
    def attempt_login(self, login: str, token: str) -> ObjectID | None:
        if login == 'login' and token == 'password':
            return 12345

        if login == 'login2' and token == 'password2':
            return 23456

        return None

    def update_object(self, oid: ObjectID, field: str, value):
        print(f'Update object {oid}: {field}={value}')
