'''

'''

import socket
from datetime import datetime

def crc16(data: bytes):
    crc = 0xFFFF
    for pos in data:
        crc ^= pos
        for _ in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return crc.to_bytes(2, "little")

HOST = "192.168.0.3"
PORT = 8010

conn_t0 = datetime.now()
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((HOST, PORT))

# Modbus RTU frame: [addr][func][addr_hi][addr_lo][len_hi][len_lo][crc_lo][crc_hi]
frame = bytes([2, 3, 0x00, 0x00, 0x00, 0x0a])
frame += crc16(frame)

sock.send(frame)

resp = sock.recv(1024)

et = (datetime.now() - conn_t0).microseconds / 1000.0;
print("Resp:", resp)
print(f"Connection time: {et} ms")