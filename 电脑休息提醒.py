import datetime
import tkinter as tk
from tkinter import messagebox
import threading

try:
    import winsound
except ImportError:
    winsound = None

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None


def create_tray_icon():
    width = 64
    height = 64
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    draw.ellipse((8, 8, 56, 56), fill="#4a90e2")
    draw.rectangle((28, 18, 36, 38), fill="white")
    draw.rectangle((30, 36, 34, 44), fill="white")
    return image


class AlarmClockApp:
    def __init__(self, root):
        self.root = root
        self.root.title("电脑休息提醒")
        self.root.geometry("420x380")  # 调整窗口高度以容纳新按钮
        self.root.resizable(False, False)

        self.hour_var = tk.StringVar(value="0")
        self.minute_var = tk.StringVar(value="60")
        self.alarm_enabled = tk.BooleanVar(value=True)
        self.show_alert = tk.BooleanVar(value=True)
        self.sound_alert = tk.BooleanVar(value=True)
        self.last_alert_time = None
        self.tray_icon = None
        self.confirmed = False
        self.blink_id = None
        self.paused = tk.BooleanVar(value=False)  # 新增暂停状态变量

        tk.Label(root, text="提醒间隔设置", font=("微软雅黑", 12, "bold")).pack(pady=10)

        time_frame = tk.Frame(root)
        time_frame.pack(pady=10)

        tk.Label(time_frame, text="小时：", font=("微软雅黑", 10)).grid(row=0, column=0, padx=5)
        hour_input_frame = tk.Frame(time_frame)
        hour_input_frame.grid(row=0, column=1, padx=5)
        tk.Button(hour_input_frame, text="-", command=self.decrease_hour, width=3, font=("微软雅黑", 10)).pack(side="left")
        self.hour_entry = tk.Entry(hour_input_frame, textvariable=self.hour_var, width=4, font=("微软雅黑", 10), justify="center")
        self.hour_entry.pack(side="left", padx=2)
        tk.Button(hour_input_frame, text="+", command=self.increase_hour, width=3, font=("微软雅黑", 10)).pack(side="left")

        tk.Label(time_frame, text="分钟：", font=("微软雅黑", 10)).grid(row=1, column=0, padx=5, pady=5)
        minute_input_frame = tk.Frame(time_frame)
        minute_input_frame.grid(row=1, column=1, padx=5, pady=5)
        tk.Button(minute_input_frame, text="-", command=self.decrease_minute, width=3, font=("微软雅黑", 10)).pack(side="left")
        self.minute_entry = tk.Entry(minute_input_frame, textvariable=self.minute_var, width=4, font=("微软雅黑", 10), justify="center")
        self.minute_entry.pack(side="left", padx=2)
        tk.Button(minute_input_frame, text="+", command=self.increase_minute, width=3, font=("微软雅黑", 10)).pack(side="left")

        confirm_button = tk.Button(time_frame, text="确认", command=self.confirm_time, width=8, font=("微软雅黑", 10))
        confirm_button.grid(row=0, column=2, rowspan=2, padx=10)

        options = tk.Frame(root)
        options.pack(padx=20, pady=10, fill="x")
        tk.Checkbutton(options, text="启用提醒", variable=self.alarm_enabled, font=("微软雅黑", 10)).pack(anchor="w")
        tk.Checkbutton(options, text="显示弹窗提醒", variable=self.show_alert, font=("微软雅黑", 10)).pack(anchor="w")
        tk.Checkbutton(options, text="播放声音提示", variable=self.sound_alert, font=("微软雅黑", 10)).pack(anchor="w")

        # 新增按钮框架：包含暂停/恢复和最小化按钮
        button_frame = tk.Frame(root)
        button_frame.pack(pady=10, fill="x", padx=20)
        # 暂停/恢复按钮
        self.pause_button = tk.Button(button_frame, text="暂停提醒", command=self.toggle_pause, height=2, 
                                      font=("微软雅黑", 11, "bold"), bg="#ff6b6b", fg="white")
        self.pause_button.pack(side="left", fill="x", expand=True, padx=5)
        # 最小化到托盘按钮
        tk.Button(button_frame, text="最小化到托盘", command=self.minimize_to_tray, height=2, 
                  font=("微软雅黑", 11, "bold")).pack(side="left", fill="x", expand=True, padx=5)

        self.status_label = tk.Label(root, text="请设置提醒间隔后按确认。", font=("微软雅黑", 9), fg="#333333")
        self.status_label.pack(pady=8)

        self.root.protocol("WM_DELETE_WINDOW", self.minimize_to_tray)
        self.start_blink()
        self.root.after(1000 * 60, self.check_alarm)

    def increase_hour(self):
        try:
            val = int(self.hour_var.get())
            if val < 24:
                self.hour_var.set(str(val + 1))
        except ValueError:
            self.hour_var.set("0")

    def decrease_hour(self):
        try:
            val = int(self.hour_var.get())
            if val > 0:
                self.hour_var.set(str(val - 1))
        except ValueError:
            self.hour_var.set("0")

    def increase_minute(self):
        try:
            val = int(self.minute_var.get())
            if val < 59:
                self.minute_var.set(str(val + 1))
        except ValueError:
            self.minute_var.set("0")

    def decrease_minute(self):
        try:
            val = int(self.minute_var.get())
            if val > 0:
                self.minute_var.set(str(val - 1))
        except ValueError:
            self.minute_var.set("0")

    def validate_input(self, var, min_val, max_val):
        try:
            val = int(var.get())
            if val < min_val:
                var.set(str(min_val))
            elif val > max_val:
                var.set(str(max_val))
        except ValueError:
            var.set(str(min_val))

    def start_blink(self):
        if not self.confirmed:
            current_color = self.hour_entry.cget("fg")
            new_color = "white" if current_color == "black" else "black"
            self.hour_entry.config(fg=new_color)
            self.minute_entry.config(fg=new_color)
            self.blink_id = self.root.after(500, self.start_blink)

    def stop_blink(self):
        if self.blink_id:
            self.root.after_cancel(self.blink_id)
        self.hour_entry.config(fg="black")
        self.minute_entry.config(fg="black")

    def confirm_time(self):
        self.validate_input(self.hour_var, 0, 24)
        self.validate_input(self.minute_var, 0, 59)
        self.confirmed = True
        self.stop_blink()
        self.last_alert_time = datetime.datetime.now()
        total_minutes = int(self.hour_var.get()) * 60 + int(self.minute_var.get())
        if total_minutes == 0:
            self.status_label.config(text="提醒间隔不能为 0，请重新设置。", fg="#aa0000")
            self.confirmed = False
            self.start_blink()
        else:
            self.status_label.config(text=f"提醒已确认，每 {int(self.hour_var.get())}小时 {int(self.minute_var.get())}分钟提醒一次。", fg="#006600")
            # 恢复暂停按钮状态
            if self.paused.get():
                self.toggle_pause()

    def get_interval_minutes(self):
        hours = int(self.hour_var.get())
        minutes = int(self.minute_var.get())
        return hours * 60 + minutes

    def check_alarm(self):
        if not self.confirmed or not self.alarm_enabled.get() or self.paused.get():
            self.root.after(1000 * 60, self.check_alarm)
            return

        now = datetime.datetime.now()
        interval_minutes = self.get_interval_minutes()
        elapsed = (now - self.last_alert_time).total_seconds() / 60
        if elapsed >= interval_minutes:
            self.trigger_alarm()
            self.last_alert_time = now

        self.root.after(1000 * 60, self.check_alarm)

    def trigger_alarm(self):
        # 创建线程同步执行弹窗和声音
        alert_thread = threading.Thread(target=self._execute_alert, daemon=True)
        alert_thread.start()

    def _execute_alert(self):
        # 存储需要执行的操作
        actions = []
        if self.show_alert.get():
            actions.append(self.show_topmost_alert)
        if self.sound_alert.get():
            actions.append(self.play_sound)
        
        # 同步执行所有提醒操作
        threads = []
        for action in actions:
            t = threading.Thread(target=action, daemon=True)
            t.start()
            threads.append(t)
        
        # 等待所有线程完成
        for t in threads:
            t.join()
        
        # 更新状态标签（需要在主线程执行）
        self.root.after(0, lambda: self.status_label.config(
            text="提醒已触发，建议离开电脑休息。", fg="#006600"
        ))

    def show_topmost_alert(self):
        """显示置顶的弹窗提醒"""
        try:
            # 创建顶级窗口作为提醒弹窗
            alert_window = tk.Toplevel(self.root)
            alert_window.title("休息提醒")
            alert_window.geometry("300x150")
            alert_window.resizable(False, False)
            alert_window.attributes("-topmost", True)  # 设置置顶
            alert_window.protocol("WM_DELETE_WINDOW", alert_window.destroy)

            # 设置弹窗内容
            tk.Label(alert_window, text="时间到了！", font=("微软雅黑", 16, "bold")).pack(pady=20)
            tk.Label(alert_window, text="建议休息一下，保护眼睛和身体！", font=("微软雅黑", 12)).pack(pady=5)
            tk.Button(alert_window, text="确定", command=alert_window.destroy, 
                      font=("微软雅黑", 11), width=10).pack(pady=10)

            # 使弹窗获得焦点
            alert_window.focus_force()
            alert_window.grab_set()  # 模态窗口
        except tk.TclError:
            # 备用方案：使用messagebox并尝试置顶
            try:
                # 先创建临时窗口设置置顶
                temp_win = tk.Toplevel(self.root)
                temp_win.attributes("-topmost", True)
                temp_win.withdraw()
                messagebox.showinfo("休息提醒", "时间到了，建议休息一下！", parent=temp_win)
                temp_win.destroy()
            except:
                pass

    def play_sound(self):
        """播放提示音"""
        if winsound:
            for freq, duration in [(600, 250), (800, 250), (1000, 300)]:
                winsound.Beep(freq, duration)
        else:
            print("[提醒声音] 时间到，请休息！")

    def toggle_pause(self):
        """切换暂停/恢复状态"""
        if self.paused.get():
            # 恢复提醒
            self.paused.set(False)
            self.pause_button.config(text="暂停提醒", bg="#ff6b6b", fg="white")
            self.last_alert_time = datetime.datetime.now()  # 重置计时
            self.status_label.config(text="提醒已恢复", fg="#006600")
        else:
            # 暂停提醒
            self.paused.set(True)
            self.pause_button.config(text="恢复提醒", bg="#4ecdc4", fg="white")
            self.status_label.config(text="提醒已暂停", fg="#ff9900")

    def minimize_to_tray(self):
        if pystray is None:
            self.status_label.config(text="未安装 pystray，无法托盘化。", fg="#aa0000")
            self.root.withdraw()
            return

        self.root.withdraw()
        if self.tray_icon is None:
            image = create_tray_icon()
            menu = pystray.Menu(
                pystray.MenuItem("打开主窗口", self.restore_window),
                pystray.MenuItem("退出", self.quit_app),
            )
            self.tray_icon = pystray.Icon("alarm_clock", image, "电脑休息提醒", menu)
            thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            thread.start()
        else:
            self.tray_icon.visible = True

    def restore_window(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.visible = False
        self.root.deiconify()

    def quit_app(self, icon=None, item=None):
        if self.tray_icon:
            self.tray_icon.stop()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = AlarmClockApp(root)
    root.mainloop()