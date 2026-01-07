from dataclasses import dataclass

@dataclass
class WaitCmd:
    t: float

@dataclass
class MoveToCmd:
    who: str
    x: float
    y: float
    speed: float = 120

@dataclass
class SayCmd:
    who: str
    text: str

@dataclass
class FaceCmd:
    who: str
    dir: str  
