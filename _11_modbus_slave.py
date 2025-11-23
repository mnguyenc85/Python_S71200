'''
Mô phỏng modbus slave 
- Bộ nhớ holding registers:
  40000 - 40200
- Các functions hỗ trợ:
  3
  6
  16
'''

import socket
import crcmod

crc16 = crcmod.predefined.mkPredefinedCrcFun("modbus")

# ---------------------------
# HOLDING REGISTER MAP (0–13)
# ---------------------------
holding_registers = [0] * 400  # 200 registers 16-bit


def process_read_holding(slave, start_addr, quantity):
    if start_addr + quantity > len(holding_registers):
        return bytes([slave, 0x83, 0x02])  # illegal data address

    byte_count = quantity * 2
    response = bytes([slave, 0x03, byte_count])

    for i in range(quantity):
        reg_value = holding_registers[start_addr + i]
        response += reg_value.to_bytes(2, "big")

    return response


def process_write_single(slave, addr, value):
    if addr >= len(holding_registers):
        return bytes([slave, 0x86, 0x02])

    holding_registers[addr] = value

    # Modbus RTU echo
    response = bytes([slave, 0x06])
    response += addr.to_bytes(2, "big") + value.to_bytes(2, "big")
    return response


def process_write_multiple(slave, start_addr, quantity, values):
    if start_addr + quantity > len(holding_registers):
        return bytes([slave, 0x90, 0x02])  # illegal address

    for i in range(quantity):
        holding_registers[start_addr + i] = values[i]

    # Response: slave, 0x10, start_addr, quantity
    response = bytes([slave, 0x10])
    response += start_addr.to_bytes(2, "big")
    response += quantity.to_bytes(2, "big")
    return response


def process_modbus_rtu(request: bytes):
    if len(request) < 4:
        return None

    slave = request[0]
    func = request[1]
    data = request[2:-2]
    crc_recv = int.from_bytes(request[-2:], "little")

    # CRC check
    if crc16(request[:-2]) != crc_recv:
        print("CRC lỗi")
        return None

    # ---- FC 03 -------------------------------------------------
    if func == 0x03:
        start_addr = int.from_bytes(data[0:2], "big")
        quantity   = int.from_bytes(data[2:4], "big")
        response = process_read_holding(slave, start_addr, quantity)

    # ---- FC 06 -------------------------------------------------
    elif func == 0x06:
        addr  = int.from_bytes(data[0:2], "big")
        value = int.from_bytes(data[2:4], "big")
        response = process_write_single(slave, addr, value)

    # ---- FC 16 (Write Multiple Registers) ----------------------
    elif func == 0x10:
        start_addr = int.from_bytes(data[0:2], "big")
        quantity   = int.from_bytes(data[2:4], "big")
        byte_count = data[4]

        # Parse giá trị
        values = []
        pos = 5
        for i in range(quantity):
            val = int.from_bytes(data[pos:pos+2], "big")
            values.append(val)
            pos += 2

        response = process_write_multiple(slave, start_addr, quantity, values)

    else:
        response = bytes([slave, func | 0x80, 0x01])  # illegal function

    # Add CRC
    crc = crc16(response)
    response += crc.to_bytes(2, "little")
    return response


def start_server():
    HOST = "0.0.0.0"
    PORT = 8010

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(1)

    print(f"Modbus RTU-over-TCP Slave đang chạy tại {HOST}:{PORT}")

    while True:
        client, addr = server.accept()
        print("Client kết nối:", addr)

        try:
            while True:
                request = client.recv(300)
                if not request:
                    break

                # print("Nhận:", request.hex(" "))
                response = process_modbus_rtu(request)

                if response:
                    # print("Trả:", response.hex(" "))
                    client.sendall(response)

        except Exception as e:
            print("Lỗi:", e)

        print("Client ngắt")
        client.close()


if __name__ == "__main__":
    start_server()
