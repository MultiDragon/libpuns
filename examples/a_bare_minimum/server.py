from libpuns.server.database_interface import DummyDatabaseInterface
from libpuns.server.server_director import ServerMessageDirector

from . import example_cfg

server = ServerMessageDirector(DummyDatabaseInterface(), example_cfg.SExamplePlayer)
server.launch(7201)
