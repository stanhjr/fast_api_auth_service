from enum import Enum


class Type(str, Enum):
    incoming = "incoming"
    outgoing = "outgoing"
