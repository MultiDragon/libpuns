from libpuns.server.database_interface import DummyDatabaseInterface
from libpuns.server.server_director import ServerMessageDirector

from . import chat_cfg

server = ServerMessageDirector(DummyDatabaseInterface(), chat_cfg.STalker)
server.launch(7200)
