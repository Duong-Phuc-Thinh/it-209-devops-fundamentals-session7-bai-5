# Bài 5: Chẩn đoán và xử lý xung đột cổng mạng (Address Already in Use)

Dự án cung cấp công cụ Python và tài liệu kỹ thuật chuẩn nhằm chẩn đoán, phát hiện và xử lý lỗi xung đột cổng mạng (`Address already in use`) trên môi trường Linux/DevOps.

## 1. Cấu trúc thư mục
```text
.
├── README.md               # Hướng dẫn sử dụng và tổng quan bài tập
├── troubleshoot.py         # Script tự động hóa quét port, kill tiến trình và tạo báo cáo
└── troubleshoot_report.md  # Báo cáo thực hiện chẩn đoán và giải quyết lỗi
```

## 2. Tính năng của công cụ `troubleshoot.py`
- **Quét & Chẩn đoán cổng:** Tự động phát hiện tiến trình đang lắng nghe trên cổng (hỗ trợ `ss`, `lsof`, `/proc` và `ps`).
- **Giải phóng cổng an toàn:** Dừng tiến trình xung đột bằng tín hiệu chuẩn `SIGTERM` (`-15`) hoặc cưỡng chế `SIGKILL` (`-9`).
- **Chế độ mô phỏng (`--simulate`):** Tự sinh tiến trình `python3 -m http.server 8082` để kiểm thử quy trình chẩn đoán.
- **Tự động xuất báo cáo:** Tạo và cập nhật file `troubleshoot_report.md` với đầy đủ số liệu và log chẩn đoán.

## 3. Hướng dẫn sử dụng

### Chế độ kiểm tra cổng mặc định (8082):
```bash
python3 troubleshoot.py
```

### Chế độ mô phỏng lỗi xung đột cổng và xuất báo cáo:
```bash
python3 troubleshoot.py -s -p 8082
```

### Chế độ tự động chẩn đoán và tiêu diệt tiến trình chiếm dụng:
```bash
python3 troubleshoot.py -p 8082 --kill
```

### Chế độ cưỡng chế ngắt (Force Kill -9):
```bash
python3 troubleshoot.py -p 8082 --kill --force
```

### Tùy chọn tham số:
- `-p, --port`: Cổng mạng cần kiểm tra (mặc định: `8082`).
- `-k, --kill`: Tự động ngắt tiến trình chiếm cổng.
- `-f, --force`: Sử dụng `SIGKILL` thay cho `SIGTERM`.
- `-s, --simulate`: Tự tạo tiến trình giả lập chiếm cổng để test.
- `-o, --output`: Đường dẫn lưu tệp báo cáo markdown.
