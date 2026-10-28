import time
from enum import Enum, auto
from communication_library.communication_manager import CommunicationManager, TransportType
from communication_library.tcp_transport import TcpSettings
from communication_library.frame import Frame
from communication_library import ids
from communication_library.exceptions import TransportTimeoutError, TransportError, UnregisteredCallbackError

class MissionState(Enum):
    IDLE = auto()
    FILLING_OXIDIZER = auto()
    FILLING_FUEL = auto()
    HEATING_OXYGEN = auto()
    LAUNCH_SEQUENCE = auto()
    FLIGHT = auto()
    LANDING = auto()
    ABORT = auto()

# Stałe
# ID sensorów
FUEL_LEVEL_ID = 0
OXIDIZER_LEVEL_ID = 1
ALTITUDE_ID = 2
OXIDIZER_PRESSURE_ID = 3
ANGLE_ID = 4
# Serwomechanizmy (ID)
FUEL_INTAKE_ID = 0
OXIDIZER_INTAKE_ID = 1
FUEL_MAIN_ID = 2
OXIDIZER_MAIN_ID = 3

# Przekaźniki (ID)
OXIDIZER_HEATER_ID = 0
IGNITER_ID = 1
PARACHUTE_ID = 2

# Pozycje zaworów i operacje przekaźników
OPEN_POS = 0
CLOSED_POS = 100
RELAY_OPEN = ids.OperationID.RELAY.value.OPEN
RELAY_CLOSE = ids.OperationID.RELAY.value.CLOSE

# Parametry fizyczne misji
TARGET_PRESSURE = 55.0
DROP_HEIGHT = 10.0
LANDING_ALTITUDE = 0.1

sensor_readings = {
    FUEL_LEVEL_ID: 0.0,
    OXIDIZER_LEVEL_ID: 0.0,
    ALTITUDE_ID: 0.0,
    OXIDIZER_PRESSURE_ID: 0.0,
    ANGLE_ID: 0.0
}

def sensors_feed(frame: Frame):
    """ Saving sensor reading to dict """
    sensor_readings[frame.device_id] = frame.data

def send_and_verify(cm: CommunicationManager, frame_to_send: Frame, timeout: float = 1.0) -> bool:
    """ Wysyła ramkę i oczekuje na potwerdzenie (ACK) od sprzętu. """
    cm.push(frame_to_send)
    cm.send()
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            frame = cm.receive()
        except TransportTimeoutError:
            continue
        except UnregisteredCallbackError as e:
            f = e.frame
            if f.device_type == frame_to_send.device_type and f.device_id == frame_to_send.device_id:
                if f.action == ids.ActionID.ACK:
                    return True
                elif f.action == ids.ActionID.NACK:
                    print(f"[BŁĄD] Otrzymano NACK dla urządzenia {f.device_id}!")
                    return False
                    
    print(f"[TIMEOUT] Brak odpowiedzi dla urządzenia {frame_to_send.device_id}!")
    return False

def set_servo(cm: CommunicationManager, device_id: int, position: int) -> bool:
    """ Sending info servo-type and returning status """
    frame = Frame(
        destination = ids.BoardID.ROCKET,
        priority = ids.PriorityID.LOW,
        action = ids.ActionID.SERVICE,
        source = ids.BoardID.SOFTWARE,
        device_type = ids.DeviceID.SERVO,
        device_id = device_id,
        data_type = ids.DataTypeID.INT16,
        operation=  ids.OperationID.SERVO.value.POSITION,
        payload = (position,)
    )
    return send_and_verify(cm, frame)

def set_relay(cm: CommunicationManager, device_id: int, operation: int) -> bool:
    """ Sending info relay-type and returning status """
    frame = Frame(
        destination= ids.BoardID.ROCKET, 
        priority = ids.PriorityID.LOW, 
        action = ids.ActionID.SERVICE, 
        source = ids.BoardID.SOFTWARE, 
        device_type = ids.DeviceID.RELAY, 
        device_id = device_id,
        data_type = ids.DataTypeID.FLOAT,
        operation = operation,
        payload=()
    )
    return send_and_verify(cm, frame)

def main():
    cm = CommunicationManager()
    cm.change_transport_type(TransportType.TCP)

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

    max_height = 0.0
    current_state = MissionState.IDLE

    while True:
        try:
            frame_received = cm.receive()
        except TransportTimeoutError:
            pass
        except UnregisteredCallbackError as e:
            pass

        match current_state:
            case MissionState.IDLE:
                if set_servo(cm, OXIDIZER_INTAKE_ID, OPEN_POS):
                    current_state = MissionState.FILLING_OXIDIZER
                else:
                    current_state = MissionState.ABORT

            case MissionState.FILLING_OXIDIZER:
                oxidizer_level = sensor_readings[OXIDIZER_LEVEL_ID]
                if oxidizer_level >= 100.0:
                    if set_servo(cm, OXIDIZER_INTAKE_ID, CLOSED_POS) and set_servo(cm, FUEL_INTAKE_ID, OPEN_POS):
                        current_state = MissionState.FILLING_FUEL
                    else:
                        current_state = MissionState.ABORT

            case MissionState.FILLING_FUEL:
                fuel_level = sensor_readings[FUEL_LEVEL_ID]
                if fuel_level >= 100.0:
                    if set_servo(cm, FUEL_INTAKE_ID, CLOSED_POS) and set_relay(cm, OXIDIZER_HEATER_ID, RELAY_OPEN):
                        current_state = MissionState.HEATING_OXYGEN
                    else:
                        current_state = MissionState.ABORT

            case MissionState.HEATING_OXYGEN:
                cisnienie = sensor_readings[OXIDIZER_PRESSURE_ID]
                if cisnienie > TARGET_PRESSURE:
                    if set_relay(cm, OXIDIZER_HEATER_ID, RELAY_CLOSE):
                        current_state = MissionState.LAUNCH_SEQUENCE
                    else:
                        current_state = MissionState.ABORT

            case MissionState.LAUNCH_SEQUENCE:
                print("Rozpoczynam sekwencję zapłonu...")
                ok_fuel = set_servo(cm, FUEL_MAIN_ID, OPEN_POS)
                ok_ox = set_servo(cm, OXIDIZER_MAIN_ID, OPEN_POS)
                ok_ign = set_relay(cm, IGNITER_ID, RELAY_OPEN)
                
                if ok_fuel and ok_ox and ok_ign:
                    print("Zapłon powiódł się!")
                    current_state = MissionState.FLIGHT
                else:
                    set_servo(cm, FUEL_MAIN_ID, CLOSED_POS)
                    set_servo(cm, OXIDIZER_MAIN_ID, CLOSED_POS)
                    current_state = MissionState.ABORT
                
            case MissionState.FLIGHT:
                if max_height - DROP_HEIGHT > sensor_readings[ALTITUDE_ID]:
                    ok_fuel = set_servo(cm, FUEL_MAIN_ID, CLOSED_POS)
                    ok_ox = set_servo(cm, OXIDIZER_MAIN_ID, CLOSED_POS)
                    ok_ign = set_relay(cm, IGNITER_ID, RELAY_CLOSE)
                    ok_para = set_relay(cm, PARACHUTE_ID, RELAY_OPEN)
                    
                    if ok_fuel and ok_ox and ok_ign and ok_para:
                        current_state = MissionState.LANDING
                    else:
                        current_state = MissionState.ABORT
                else:
                    max_height = max(sensor_readings[ALTITUDE_ID], max_height)

            case MissionState.LANDING:
                if sensor_readings[ALTITUDE_ID] <= LANDING_ALTITUDE:
                    print("Misja zakończona sukcesem!")
                    set_relay(cm, PARACHUTE_ID, RELAY_CLOSE)
                    break

            case MissionState.ABORT:
                print("Something went wrong!")
                break
            
                
if __name__ == "__main__":
    main()