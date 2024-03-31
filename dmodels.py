from typing import List, AnyStr

class CHD: # Communication History Data
    messages: List[AnyStr]
    def __init__(self) -> None:
        self.messages = []

class BPI: # Basic Peer Info
    identifier: str
    name: str
    history: CHD
    flags: int #BITMAP
    def __init__(self, identifier, name=None, history=None, flags= 0) -> None:
        self.identifier = identifier
        self.name = name
        self.history = history
        self.flags = flags