1. TestComm: Code cho S7-1200 kết nối qua snap7 (Profinet)
	- Thiết lập DB1 cho phép đọc
2. TestMbSlave: Code cho S7-1200 hoạt động ở chế độ Modbus Slave sử dụng module truyền thông CP 1241 RS485
	- Kết nối qua RS485
3. TestMbSlaveTCP: Code cho S7-1200 hoạt động ở chế độ Modbus Slave qua ethernet (cổng Ethernet sẵn có của S7-1200)
	- Kết nối qua RS485

** 2, 3 vì nếu dùng CPU S7-1200 < v4.0 thì không kết nối được qua snap7?