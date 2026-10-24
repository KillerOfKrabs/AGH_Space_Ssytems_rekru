from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import TransportTimeoutError, TransportError, UnregisteredCallbackError

from enum import Enum, auto

class MissionState(Enum):
    IDLE = auto()
    FILLING_OXIDIZER = auto()
    FILLING_FUEL = auto()
    HEATING_OXYGEN = auto()
    LAUCH_SEQUENCE = auto()
    FLIGHT = auto()
    LANDING = auto()

def main():
    cm = CommunicationManager()
    cm.change_transport_type(TransportType.TCP)
    cm.connect(TcpSettings("127.0.0.1", 3000))

    while True:
        try:
            frame = cm.receive()
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError as e:
            print(f"Odebrano ramkę: {e.frame}")


if __name__ == "main":
    main()