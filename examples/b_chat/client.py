import os

from direct.gui.DirectButton import DirectButton
from direct.gui.DirectEntry import DirectEntry
from direct.gui.DirectLabel import DirectLabel
from direct.showbase.ShowBase import ShowBase

from libpuns.client.client_director import ClientMessageDirector
from libpuns.client.client_node import CNetworkNode

from .chat_cfg import CTalker


class ChatBase(ShowBase):
    def __init__(self):
        super().__init__()
        self.client = ClientMessageDirector(CTalker, self.on_connect)
        sc = '2' if os.environ.get('SECOND_CLIENT', False) else ''
        self.client.connect('localhost', 7200, f'login{sc}', f'password{sc}')

        self.log = DirectLabel(text='', pos=(0, 0, 0), scale=0.05, textMayChange=True)
        self.username = DirectEntry(text='', pos=(-0.5, 0, -0.65), scale=0.1)
        self.username_btn = DirectButton(text='Save', pos=(0.6, 0, -0.65), scale=0.1, command=self.on_username_btn)
        self.message = DirectEntry(text='', pos=(-0.5, 0, -0.85), scale=0.1)
        self.message_btn = DirectButton(text='Send', pos=(0.6, 0, -0.85), scale=0.1, command=self.on_message_btn)

        self.talker = None

    def append_log(self, msg: str) -> None:
        self.log['text'] += msg + '\n'

    def on_username_btn(self) -> None:
        if not self.talker:
            self.append_log('You are not connected to the server!')
            return

        self.talker.send_update('request_username', self.username.get())

    def on_message_btn(self) -> None:
        if not self.talker:
            self.append_log('You are not connected to the server!')
            return

        self.talker.send_message(self.message.get())

    def on_connect(self, node: CNetworkNode) -> None:
        self.append_log('Connected to the server')
        self.talker = node


base = ChatBase()
base.run()
