import ctypes

FILE_DEVICE_UNKNOWN = 0x22
METHOD_BUFFERED = 0
FILE_SPECIAL_ACCESS = 0x0

def CTL_CODE(DeviceType, Function, Method, Access):
    return (DeviceType << 16) | (Access << 14) | (Function << 2) | Method

IOCTL_MOUSE_MOVE = CTL_CODE(FILE_DEVICE_UNKNOWN, 0x696, METHOD_BUFFERED, FILE_SPECIAL_ACCESS)

class Request(ctypes.Structure):
    _fields_ = [
        ("x", ctypes.c_long),
        ("y", ctypes.c_long),
        ("button_flags", ctypes.c_ushort)
    ]
