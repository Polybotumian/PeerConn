from typing import List, AnyStr
from datetime import datetime


class Message:
    text: AnyStr
    dtime: datetime
    who: int

    def __init__(self, text: str, dtime: datetime, who: int) -> None:
        self.text = text
        self.dtime = dtime
        self.who = who


class CHD:
    """
    Data model that stores all messages.
    """
    messages: List[Message]

    def __init__(self) -> None:
        self.messages = []


class BPI:
    """
    Data model that contains peer info.
    """
    identifier: str
    name: str
    history: CHD
    flags: int  # BITMAP

    def __init__(self, identifier, name=None, history=None, flags=0) -> None:
        self.identifier = identifier
        self.name = name
        self.history = history
        self.flags = flags
