# Báo cáo Chẩn đoán và Xử lý Xung đột Cổng mạng (Address Already in Use)

- **Học viên:** DevOps Engineer
- **Cổng mục tiêu:** `8082`
- **Hệ thống thử nghiệm:** Ubuntu 22.04 LTS / Linux Kernel 5.15+
- **Dịch vụ đích:** `spring-app.service` (Java Application)

---

## 1. Bối cảnh phát sinh lỗi
Khi thực hiện khởi động hoặc khởi động lại ứng dụng Spring Boot (`spring-app.service`), ứng dụng gặp sự cố crash và ghi log lỗi:

```text
org.springframework.boot.web.server.PortInUseException: Web server failed to start. Port 8082 was already in use.
    at org.springframework.boot.web.embedded.tomcat.TomcatWebServer.start(TomcatWebServer.java:242)
```

Nguyên nhân: Cổng TCP 8082 đã bị một tiến trình chạy ngầm chiếm giữ.

---

## 2. Mô phỏng sự cố (Simulate Conflict)
Khởi chạy tiến trình giả lập chiếm dụng cổng 8082 dưới nền bằng lệnh:

```bash
python3 -m http.server 8082 > /dev/null 2>&1 &
```

Kiểm tra mã PID tiến trình nền vừa tạo:
```bash
echo $!
# PID tra ve: 41294
```

---

## 3. Quy trình Chẩn đoán Cổng mạng

### Bước 3.1: Dùng lệnh `ss`
Chẩn đoán các socket đang ở trạng thái lắng nghe (TCP Listening) kèm thông tin định danh tiến trình:
```bash
sudo ss -tlnp | grep 8082
```

**Kết quả đầu ra:**
```text
LISTEN 0      5            0.0.0.0:8082      0.0.0.0:*    users:(("python3",pid=41294,fd=3))
```

### Bước 3.2: Dùng lệnh `lsof` (Xác thực chéo)
Kiểm tra file descriptor và tiến trình mở cổng:
```bash
sudo lsof -i :8082
```

**Kết quả đầu ra:**
```text
COMMAND     PID   USER   FD   TYPE DEVICE SIZE/OFF NODE NAME
python3   41294 ubuntu    3u  IPv4  58392      0t0  TCP *:8082 (LISTEN)
```

### Bảng tổng hợp thông tin tiến trình xung đột
| Thuộc tính | Chi tiết |
| :--- | :--- |
| **PID** | `41294` |
| **User** | `ubuntu` |
| **Tên tiến trình** | `python3` |
| **Lệnh thực thi** | `python3 -m http.server 8082` |
| **Giao thức / Port**| `TCP 0.0.0.0:8082` (LISTEN) |

---

## 4. Xử lý giải phóng tài nguyên

### Bước 4.1: Gửi tín hiệu ngắt thông thường (SIGTERM)
```bash
kill -15 41294
```

*Ghi chú:* Nếu tiến trình bị treo hoặc không phản hồi sau 5 giây, sử dụng tín hiệu cưỡng chế dừng:
```bash
kill -9 41294
```

### Bước 4.2: Xác nhận cổng đã được giải phóng
```bash
sudo ss -tlnp | grep 8082
```
*(Kết quả rỗng: Không còn tiến trình nào chiếm giữ cổng 8082)*

---

## 5. Khởi động lại dịch vụ đích và xác nhận kết quả

### Bước 5.1: Khởi động lại dịch vụ Spring Boot
```bash
sudo systemctl restart spring-app.service
sudo systemctl status spring-app.service
```

### Bước 5.2: Kiểm tra tiến trình sở hữu cổng 8082 mới
```bash
sudo ss -tlnp | grep 8082
```

**Kết quả mong đợi:**
```text
LISTEN 0      100          *:8082            *:*          users:(("java",pid=42105,fd=28))
```

**Kết luận:**
- Cổng `8082` đã được giải phóng khỏi tiến trình chiếm dụng giả lập (`python3`).
- Ứng dụng chính (`java`) đã khởi chạy và chiếm quyền lắng nghe trên cổng `8082` an toàn, không còn lỗi `Address already in use`.
