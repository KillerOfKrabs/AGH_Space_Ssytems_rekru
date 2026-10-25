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

sensor_readings = {
    0: 0.0,  # fuel_level
    1: 0.0,  # oxidizer_level
    2: 0.0,  # altitude
    3: 0.0,  # oxidizer_pressure
    4: 0.0   # angle
}

def sensors_feed(frame : Frame):
    device_id = frame.device_id
    device_data = frame.data
    sensor_readings[device_id] = device_data

def main():
    cm = CommunicationManager()
    cm.change_transport_type(TransportType.TCP)

    """ Fram-y odpowiadające kolejnym zadaniom """
    for klucz in sensor_readings:
        frame = Frame(
                ids.BoardID.SOFTWARE, 
                ids.PriorityID.LOW, 
                ids.ActionID.FEED, 
                ids.BoardID.ROCKET, 
                ids.DeviceID.SENSOR, 
                klucz,
                ids.DataTypeID.FLOAT,
                ids.OperationID.SENSOR.value.READ
            )
        cm.register_callback(sensors_feed, frame)

    cm.connect(TcpSettings("127.0.0.1", 3000))

    current_state = MissionState.IDLE

    while True:
        try:
            frame_recivved = cm.receive()
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError as e:
            print(f"Odebrano ramkę: {e.frame}")

        match current_state:
            case MissionState.IDLE:
                current_state = MissionState.FILLING_OXIDIZER
            case MissionState.FILLING_OXIDIZER:
                pass
            case MissionState.FILLING_FUEL:
                pass
            case MissionState.HEATING_OXYGEN:
                pass
            case MissionState.LAUCH_SEQUENCE:
                pass
            case MissionState.FLIGHT:
                pass
            case MissionState.LANDING:
                pass

if __name__ == "__main__":
    main()