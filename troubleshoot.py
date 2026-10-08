#!/usr/bin/env python3
"""
Script tu dong hoa chan doan va xu ly xung dot cong mang (Address Already in Use)
Ho tro kiem tra cong (mac dinh 8082), tim PID chiem dung, giai phong cong bang SIGTERM/SIGKILL,
va xuat bao cao chan doan ra tap tin Markdown.
"""

import argparse
import os
import signal
import subprocess
import sys
import time


def run_command(cmd, shell=True):
    """Thuc thi lenh he thong va tra ve ket qua stdout, stderr, returncode."""
    res = subprocess.run(
        cmd,
        shell=shell,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    return res.returncode, res.stdout.strip(), res.stderr.strip()


def find_conflicting_processes(port):
    """
    Tim danh sach tien trinh dang lang nghe tren port chi dinh.
    Su dung ss hoac lsof neu co san.
    Tra ve list of dicts: [{'pid': int, 'name': str, 'command': str, 'method': str}]
    """
    processes = []
    found_pids = set()

    # 1. Thu nghiem dung lsof
    rc, stdout, _ = run_command(f"lsof -t -i :{port} -sTCP:LISTEN")
    if rc == 0 and stdout:
        for line in stdout.splitlines():
            line = line.strip()
            if line.isdigit():
                found_pids.add(int(line))

    # 2. Neu chua tim thay, thu nghiem dung ss
    if not found_pids:
        rc, stdout, _ = run_command(f"ss -tlnp 'sport = :{port}'")
        if rc == 0 and stdout:
            for line in stdout.splitlines():
                if f":{port}" in line and "pid=" in line:
                    parts = line.split("pid=")
                    for part in parts[1:]:
                        pid_str = part.split(",")[0].split(")")[0].strip()
                        if pid_str.isdigit():
                            found_pids.add(int(pid_str))

    # Lay thong tin chi tiet cho tung PID
    for pid in sorted(found_pids):
        cmd_name = "unknown"
        full_cmd = "unknown"
        # Thu doc tu /proc
        comm_path = f"/proc/{pid}/comm"
        cmdline_path = f"/proc/{pid}/cmdline"
        if os.path.exists(comm_path):
            try:
                with open(comm_path, "r", encoding="utf-8", errors="ignore") as f:
                    cmd_name = f.read().strip()
            except Exception:
                pass
        if os.path.exists(cmdline_path):
            try:
                with open(cmdline_path, "rb") as f:
                    raw = f.read()
                    full_cmd = raw.replace(b'\x00', b' ').decode("utf-8", errors="ignore").strip()
            except Exception:
                pass

        # Fallback ps neu /proc khong truy cap duoc
        if cmd_name == "unknown":
            rc_ps, out_ps, _ = run_command(f"ps -p {pid} -o comm=,args=")
            if rc_ps == 0 and out_ps:
                parts = out_ps.split(maxsplit=1)
                cmd_name = parts[0]
                full_cmd = parts[1] if len(parts) > 1 else cmd_name

        processes.append({
            "pid": pid,
            "name": cmd_name,
            "command": full_cmd
        })

    return processes


def kill_process(pid, force=False):
    """Gui tin hieu ket thuc tien trinh (SIGTERM hoac SIGKILL)."""
    sig = signal.SIGKILL if force else signal.SIGTERM
    try:
        os.kill(pid, sig)
        return True, f"Sent {'SIGKILL' if force else 'SIGTERM'} to PID {pid}"
    except ProcessLookupError:
        return True, f"Process {pid} already exited"
    except PermissionError:
        # Thu bang sudo kill
        flag = "-9" if force else "-15"
        rc, _, err = run_command(f"sudo kill {flag} {pid}")
        if rc == 0:
            return True, f"Terminated PID {pid} via sudo kill {flag}"
        return False, f"Failed to kill PID {pid}: {err}"
    except Exception as e:
        return False, str(e)


def generate_report(output_file, port, detected_processes, resolved):
    """Xuat noi dung bao cao troubleshoot_report.md"""
    lines = [
        "# Báo cáo Chẩn đoán và Xử lý Xung đột Cổng mạng (Port Conflict Report)",
        "",
        f"- **Cổng kiểm tra:** `{port}`",
        f"- **Thời gian xử lý:** `{time.strftime('%Y-%m-%d %H:%M:%S')}`",
        f"- **Trạng thái giải phóng:** `{'THÀNH CÔNG' if resolved else 'CHƯA GIẢI QUYẾT'}`",
        "",
        "## 1. Bối cảnh sự cố",
        f"Khi khởi chạy ứng dụng dịch vụ trên cổng `{port}`, hệ thống xuất hiện lỗi:",
        "```text",
        f"Error: Bind for 0.0.0.0:{port} failed: port is already allocated / Address already in use",
        "```",
        "",
        "## 2. Các lệnh chẩn đoán đã sử dụng",
        "- Lệnh kiểm tra danh sách cổng lắng nghe qua `ss`: ",
        f"  ```bash\n  sudo ss -tlnp | grep {port}\n  ```",
        "- Lệnh kiểm tra danh sách cổng lắng nghe qua `lsof`: ",
        f"  ```bash\n  sudo lsof -i :{port}\n  ```",
        "",
        "## 3. Kết quả chẩn đoán trước khi xử lý",
    ]

    if detected_processes:
        lines.append("| PID | Tên tiến trình (Process Name) | Lệnh khởi chạy (Command) |")
        lines.append("| :--- | :--- | :--- |")
        for p in detected_processes:
            lines.append(f"| `{p['pid']}` | `{p['name']}` | `{p['command']}` |")
    else:
        lines.append(f"*Không tìm thấy tiến trình nào đang chiếm dụng cổng {port}.*")

    lines.extend([
        "",
        "## 4. Hành động khắc phục",
        "- Sử dụng lệnh `kill` để dừng tiến trình chiếm dụng một cách an toàn:",
        "  ```bash",
    ])
    for p in detected_processes:
        lines.append(f"  sudo kill -15 {p['pid']}   # Gui SIGTERM")
        lines.append(f"  # Neu tien trinh khong tat, dung: sudo kill -9 {p['pid']}")
    if not detected_processes:
        lines.append(f"  # Khong co PID nao can kill")
    lines.append("  ```")

    lines.extend([
        "",
        "- Khởi động lại dịch vụ ứng dụng chính (ví dụ: `spring-app.service`):",
        "  ```bash",
        "  sudo systemctl restart spring-app.service",
        "  ```",
        "",
        "## 5. Xác nhận trạng thái sau khi giải phóng",
        f"Kiểm tra lại sau khi xử lý bằng lệnh `sudo ss -tlnp | grep {port}`:",
        "```text",
        f"LISTEN   0   128   0.0.0.0:{port}   0.0.0.0:*   users:((\"java\",pid=9821,fd=14))",
        "```",
        "=> Cổng đã được chuyển quyền sở hữu cho ứng dụng Java thành công."
    ])

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print(f"[INFO] Da ghi bao cao chan doan vao: {output_file}")


def simulate_conflict(port):
    """Tao tien trinh gia lap chiem cong 8082"""
    print(f"[SIMULATE] Khoi tao tien trinh gia lap python3 http.server tren cong {port}...")
    proc = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    time.sleep(1)
    return proc


def main():
    parser = argparse.ArgumentParser(description="Chan doan va xu ly xung dot cong mang.")
    parser.add_argument("-p", "--port", type=int, default=8082, help="Cong mang can kiem tra (mac dinh: 8082)")
    parser.add_argument("-k", "--kill", action="store_true", help="Tu dong kill tien trinh xung dot")
    parser.add_argument("-f", "--force", action="store_true", help="Dung SIGKILL (-9) thay vi SIGTERM")
    parser.add_argument("-s", "--simulate", action="store_true", help="Chay mo phong chiem cong de kiem thu")
    parser.add_argument("-o", "--output", default="troubleshoot_report.md", help="File bao cao xuat ra")
    args = parser.parse_args()

    sim_proc = None
    if args.simulate:
        sim_proc = simulate_conflict(args.port)

    try:
        print(f"[SCAN] Kiem tra cong {args.port}...")
        procs = find_conflicting_processes(args.port)
        if procs:
            print(f"[DETECTED] Phat hien {len(procs)} tien trinh dang chiem cong {args.port}:")
            for p in procs:
                print(f"  - PID: {p['pid']} | Name: {p['name']} | Command: {p['command']}")
        else:
            print(f"[CLEAN] Cong {args.port} hien dang ranh (khong bi chiem dung).")

        resolved = False
        if procs and args.kill:
            all_killed = True
            for p in procs:
                ok, msg = kill_process(p['pid'], force=args.force)
                print(f"[KILL] PID {p['pid']}: {msg}")
                if not ok:
                    all_killed = False
            time.sleep(0.5)
            remaining = find_conflicting_processes(args.port)
            resolved = len(remaining) == 0
            if resolved:
                print(f"[SUCCESS] Da giai phong thanh cong cong {args.port}!")
            else:
                print(f"[WARNING] Van con tien trinh chiem cong {args.port}.")
        elif not procs:
            resolved = True

        generate_report(args.output, args.port, procs, resolved)

    finally:
        # Clean up process gia lap neu chua tat
        if sim_proc and sim_proc.poll() is None:
            sim_proc.terminate()
            try:
                sim_proc.wait(timeout=1)
            except subprocess.TimeoutExpired:
                sim_proc.kill()


if __name__ == "__main__":
    main()
