import threading

stop_flag = threading.Event()

def stop():
    stop_flag.set()
