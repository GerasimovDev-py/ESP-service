import psycopg2
import time
import os
import sys
from datetime import datetime, timedelta
import threading
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw, ImageFont
import subprocess
import winsound
import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import requests

try:
    from plyer import notification
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "plyer"])
    from plyer import notification

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

# Настройки подключения к Supabase
SUPABASE_HOST = "aws-1-eu-central-1.pooler.supabase.com"
SUPABASE_PORT = 5432
SUPABASE_DB = "postgres"
SUPABASE_USER = "postgres.kiwwemieqvqvrgboedjm"
SUPABASE_PASSWORD = "m6zvsN0OUUGM4heT"

# URL для API уведомлений
API_BASE_URL = "https://esp-service-production.up.railway.app"

dwFlags = 0x0001  
ctypes.windll.kernel32.SetConsoleTitleW("Конфигуратор системы платежей")
win32api.SetConsoleCtrlHandler(None, True)

class LoginWindow:
    def __init__(self, on_login_success):
        self.on_login_success = on_login_success
        self.root = ctk.CTk()
        self.root.title("Авторизация - Конфигуратор")
        self.root.geometry("450x550")
        self.root.resizable(False, False)
        
        self.center_window()
        self.setup_ui()
        
    def center_window(self):
        self.root.update_idletasks()
        width = 450
        height = 550
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f'{width}x{height}+{x}+{y}')
    
    def setup_ui(self):
        title = ctk.CTkLabel(
            self.root,
            text="🔐 Конфигуратор системы платежей",
            font=ctk.CTkFont(size=22, weight="bold")
        )
        title.pack(pady=(40, 10))
        
        subtitle = ctk.CTkLabel(
            self.root,
            text="Вход для сотрудников",
            font=ctk.CTkFont(size=16)
        )
        subtitle.pack(pady=(0, 30))
        
        key_label = ctk.CTkLabel(
            self.root,
            text="Ключ доступа:",
            font=ctk.CTkFont(size=14)
        )
        key_label.pack(pady=(10, 5))
        
        self.key_entry = ctk.CTkEntry(
            self.root,
            width=300,
            height=45,
            placeholder_text="XXXX-XXX-XXX",
            font=ctk.CTkFont(size=14)
        )
        self.key_entry.pack(pady=10)
        self.key_entry.bind('<Return>', lambda e: self.login())
        
        login_btn = ctk.CTkButton(
            self.root,
            text="🚀 Войти",
            command=self.login,
            width=250,
            height=45,
            font=ctk.CTkFont(size=16, weight="bold"),
            fg_color="#28a745",
            hover_color="#218838"
        )
        login_btn.pack(pady=20)
        
        demo_frame = ctk.CTkFrame(self.root, fg_color="#2b2b2b", corner_radius=10)
        demo_frame.pack(pady=20, padx=30, fill="x")
        
        demo_title = ctk.CTkLabel(
            demo_frame,
            text="Демо-ключи:",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color="#ffc107"
        )
        demo_title.pack(pady=(10, 5))
        
        demo_text = ctk.CTkLabel(
            demo_frame,
            text="🔧 TECH-2025-001 (Технический)\n⚖️ LEGAL-2025-001 (Юридический)\n💰 ACC-2025-001 (Делопроизводство)",
            font=ctk.CTkFont(size=13),
            text_color="gray"
        )
        demo_text.pack(pady=10)
        
        self.status_label = ctk.CTkLabel(
            self.root,
            text="",
            font=ctk.CTkFont(size=13),
            text_color="#dc3545"
        )
        self.status_label.pack(pady=10)
    
    def login(self):
        key = self.key_entry.get().strip()
        
        if not key:
            self.status_label.configure(text="❌ Введите ключ доступа")
            return
        
        try:
            conn = psycopg2.connect(
                host=SUPABASE_HOST,
                port=SUPABASE_PORT,
                dbname=SUPABASE_DB,
                user=SUPABASE_USER,
                password=SUPABASE_PASSWORD
            )
            cursor = conn.cursor()
            cursor.execute("""
                SELECT department, employee_name, key_value 
                FROM access_keys 
                WHERE key_value = %s AND is_active = TRUE
            """, (key,))
            
            result = cursor.fetchone()
            conn.close()
            
            if result:
                department, employee_name, key_value = result
                self.root.destroy()
                self.on_login_success({
                    'full_name': employee_name,
                    'department': department,
                    'access_key': key_value
                })
            else:
                self.status_label.configure(text="❌ Неверный ключ доступа")
                
        except Exception as e:
            self.status_label.configure(text=f"❌ Ошибка подключения: {e}")
    
    def run(self):
        self.root.mainloop()

class ModernDesktopNotificator:
    def __init__(self, employee=None):
        self.employee = employee
        self.running = True
        self.known_requests = set()
        self.notification_enabled = True
        self.sound_enabled = True
        self.last_check = datetime.now() - timedelta(minutes=5)
        self.current_tab = "active"
        
        self.create_tray_icon()
        self.setup_main_window()
        
    def get_pg_connection(self):
        return psycopg2.connect(
            host=SUPABASE_HOST,
            port=SUPABASE_PORT,
            dbname=SUPABASE_DB,
            user=SUPABASE_USER,
            password=SUPABASE_PASSWORD
        )
    
    def play_notification_sound(self):
        try:
            winsound.MessageBeep(winsound.MB_ICONINFORMATION)
        except:
            pass
        
    def show_notification(self, title, message):
        try:
            notification.notify(
                title=title,
                message=message,
                app_name="Конфигуратор системы платежей",
                app_icon=None,
                timeout=10
            )
            print(f"📬 Уведомление отправлено: {title}")
        except Exception as e:
            print(f"Ошибка уведомления: {e}")
            if hasattr(self, 'tray_icon'):
                try:
                    self.tray_icon.notify(message, title)
                except:
                    pass
    
    def setup_main_window(self):
        self.root = ctk.CTk()
        self.root.title(f"Конфигуратор - {self.employee['full_name']} ({self.get_department_name()})")

        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}+0+0")
        self.root.wm_title(f"Конфигуратор - {self.employee['full_name']}")
        self.root.protocol('WM_DELETE_WINDOW', self.hide_window)
        self.setup_ui()
        self.start_auto_monitoring()
        self.load_data()
    
    def get_department_name(self):
        dept_map = {
            'legal': 'Юридический',
            'technical': 'Технический',
            'accounting': 'Делопроизводство'
        }
        return dept_map.get(self.employee['department'], self.employee['department'])
    
    def create_tray_icon(self):
        image = Image.new('RGB', (64, 64), color='#0078d4')
        draw = ImageDraw.Draw(image)
        
        try:
            font = ImageFont.truetype("arial.ttf", 40)
        except:
            font = ImageFont.load_default()
        
        draw.text((32, 32), "К", fill='white', font=font, anchor="mm")
        
        menu = pystray.Menu(
            pystray.MenuItem("Открыть", self.show_window),
            pystray.MenuItem("Выход", self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("configurator", image, "Конфигуратор системы платежей", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()
    
    def hide_window(self):
        self.root.withdraw()
        self.show_notification("Конфигуратор", "Приложение работает в фоновом режиме")
    
    def show_window(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
    
    def quit_app(self):
        self.running = False
        self.tray_icon.stop()
        self.root.quit()
        sys.exit(0)
    
    def setup_ui(self):
        top_frame = ctk.CTkFrame(self.root, height=60, corner_radius=0)
        top_frame.pack(fill="x", padx=0, pady=0)
        
        title = ctk.CTkLabel(
            top_frame,
            text=f"📬 Конфигуратор - {self.employee['full_name']} ({self.get_department_name()})",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title.pack(side="left", padx=20, pady=15)
        
        control_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        control_frame.pack(side="right", padx=20, pady=10)
        
        buttons = [
            ("🌐 Сайт", self.open_website),
            ("📊 Статистика", self.show_statistics),
            ("⚙ Настройки", self.show_settings),
        ]
        
        for text, command in buttons:
            btn = ctk.CTkButton(
                control_frame,
                text=text,
                command=command,
                width=100,
                height=35,
                corner_radius=8
            )
            btn.pack(side="left", padx=2)
        
        tab_frame = ctk.CTkFrame(self.root, height=40, fg_color="transparent")
        tab_frame.pack(fill="x", padx=20, pady=(10, 0))
        
        self.active_tab_btn = ctk.CTkButton(
            tab_frame,
            text="📋 Активные заявки",
            command=lambda: self.switch_tab("active"),
            width=200,
            height=35,
            fg_color="#007bff" if self.current_tab == "active" else "#2b2b2b"
        )
        self.active_tab_btn.pack(side="left", padx=2)
        
        self.archive_tab_btn = ctk.CTkButton(
            tab_frame,
            text="🗄 Архив",
            command=lambda: self.switch_tab("archive"),
            width=200,
            height=35,
            fg_color="#6c757d" if self.current_tab == "archive" else "#2b2b2b"
        )
        self.archive_tab_btn.pack(side="left", padx=2)
        
        status_frame = ctk.CTkFrame(self.root, height=30, fg_color="#1a1a1a")
        status_frame.pack(fill="x", side="bottom")
        
        self.status_indicator = ctk.CTkLabel(
            status_frame,
            text="●",
            text_color="green",
            font=ctk.CTkFont(size=14)
        )
        self.status_indicator.pack(side="left", padx=10, pady=5)
        
        self.status_label = ctk.CTkLabel(
            status_frame,
            text=f"Активно • Отдел: {self.get_department_name()} • Автообновление каждые 10 сек",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.pack(side="left", padx=5, pady=5)
        
        self.counter_label = ctk.CTkLabel(
            status_frame,
            text="Заявок: 0",
            font=ctk.CTkFont(size=12)
        )
        self.counter_label.pack(side="right", padx=20, pady=5)
        
        self.create_interactive_table()
    
    def switch_tab(self, tab):
        self.current_tab = tab
        if tab == "active":
            self.active_tab_btn.configure(fg_color="#007bff")
            self.archive_tab_btn.configure(fg_color="#2b2b2b")
        else:
            self.active_tab_btn.configure(fg_color="#2b2b2b")
            self.archive_tab_btn.configure(fg_color="#6c757d")
        self.load_data()
    
    def create_interactive_table(self):
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        canvas = tk.Canvas(main_frame, highlightthickness=0, bg='#2b2b2b')
        scrollbar = ctk.CTkScrollbar(main_frame, orientation="vertical", command=canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(canvas)
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
    
    def load_data(self):
        """Загрузка и отображение заявок"""
        try:
            # Очищаем контейнер
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
            # Получаем данные из БД
            conn = self.get_pg_connection()
            cursor = conn.cursor()
            
            if self.current_tab == "active":
                status_filter = "status IN ('pending', 'in_progress')"
            else:
                status_filter = "status = 'completed'"
            
            cursor.execute(f"""
                SELECT id, created_at, full_name, organization, department, 
                    request_text, status, employee_response
                FROM service_request 
                WHERE {status_filter} AND department = %s
                ORDER BY created_at DESC
                LIMIT 100
            """, (self.employee['department'],))
            
            requests = cursor.fetchall()
            
            cursor.execute("""
                SELECT COUNT(*) FROM service_request 
                WHERE status = 'pending' AND department = %s
            """, (self.employee['department'],))
            new_count = cursor.fetchone()[0]
            
            conn.close()
            
            self.counter_label.configure(text=f"Новых: {new_count}")
            
            # ========== ЗАГОЛОВКИ ==========
            headers_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#1f1f1f", height=35)
            headers_frame.pack(fill="x", pady=(0, 2))
            
            # Создаем заголовки с правильными отступами
            headers = [
                ("ID", 50),
                ("Дата", 130),
                ("ФИО", 150),
                ("Организация", 150),
                ("Отдел", 120),
                ("Статус", 100)
            ]
            
            # Добавляем пустой лейбл для отступа под кружок
            ctk.CTkLabel(headers_frame, text="  ", width=30).pack(side="left")
            
            for header, width in headers:
                ctk.CTkLabel(
                    headers_frame,
                    text=header,
                    width=width,
                    anchor="w",
                    font=ctk.CTkFont(size=12, weight="bold"),
                    text_color="white"
                ).pack(side="left")
            
            # ========== ЗАЯВКИ ==========
            department_map = {
                'legal': 'Юридический',
                'technical': 'Технический',
                'accounting': 'Делопроизводство'
            }
            
            status_colors = {
                'pending': '#dc3545',
                'in_progress': '#ffc107',
                'completed': '#28a745'
            }
            
            status_names = {
                'pending': 'Ожидает',
                'in_progress': 'В работе',
                'completed': 'Завершена'
            }
            
            for req in requests:
                req_id, created, full_name, org, dept, text, status, response = req
                
                # Цвет фона
                if status == 'in_progress':
                    bg_color = "#1a3b5c"
                elif status == 'pending':
                    bg_color = "#3d1a1a"
                else:
                    bg_color = "#2b2b2b"
                
                # Строка заявки
                row_frame = ctk.CTkFrame(
                    self.scrollable_frame,
                    fg_color=bg_color,
                    height=35
                )
                row_frame.pack(fill="x", pady=1)
                row_frame.pack_propagate(False)
                
                # Статус-индикатор
                status_color = status_colors.get(status, '#808080')
                ctk.CTkLabel(
                    row_frame,
                    text="●",
                    text_color=status_color,
                    font=ctk.CTkFont(size=14),
                    width=30
                ).pack(side="left", padx=(10, 0))
                
                # Данные
                row_data = [
                    (str(req_id), 50),
                    (created[:16] if created else "", 130),
                    (full_name[:25] if full_name else "", 150),
                    (org[:25] if org else "", 150),
                    (department_map.get(dept, dept), 120),
                    (status_names.get(status, status), 100)
                ]
                
                for value, width in row_data:
                    ctk.CTkLabel(
                        row_frame,
                        text=value,
                        width=width,
                        anchor="w",
                        font=ctk.CTkFont(size=12),
                        text_color="white"
                    ).pack(side="left")
                
                # Клик по строке
                row_frame.bind("<Button-1>", lambda e, r=req: self.show_request_details(r))
                for child in row_frame.winfo_children():
                    child.bind("<Button-1>", lambda e, r=req: self.show_request_details(r))
                    
        except Exception as e:
            print(f"Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
        
    def show_request_details(self, request):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Заявка #{request[0]}")
        
        width, height = 750, 750
        x = (dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (dialog.winfo_screenheight() // 2) - (height // 2)
        dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        dialog.attributes('-topmost', True)
        dialog.lift()
        dialog.focus_force()
        dialog.grab_set()
        dialog.focus_set()
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        info_frame = ctk.CTkFrame(main_frame)
        info_frame.pack(fill="x", pady=10)
        
        department_map = {
            'legal': 'Юридический',
            'technical': 'Технический',
            'accounting': 'Делопроизводство'
        }
        
        status_map = {
            'pending': '🟡 Ожидает рассмотрения',
            'in_progress': '🟠 Принята в работу',
            'completed': '🟢 Завершена',
            'redirected': '🔄 Перенаправлена'
        }
        
        status = request[6]
        status_text = status_map.get(status, status)
        request_id = request[0]
        employee_response = request[7] if len(request) > 7 else ""
        current_department = request[4]
        
        details = [
            ("ID:", request_id),
            ("Дата:", request[1]),
            ("ФИО:", request[2]),
            ("Организация:", request[3]),
            ("Отдел:", department_map.get(current_department, current_department)),
            ("Статус:", status_text),
        ]
        
        for label, value in details:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(fill="x", pady=2)
            ctk.CTkLabel(row, text=label, width=100, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left", padx=10)
            ctk.CTkLabel(row, text=str(value), anchor="w").pack(side="left", padx=10)
        
        text_label = ctk.CTkLabel(main_frame, text="📝 Текст заявки:", anchor="w", font=ctk.CTkFont(weight="bold"))
        text_label.pack(anchor="w", padx=10, pady=(20, 5))
        
        text_box = ctk.CTkTextbox(main_frame, height=100, wrap="word")
        text_box.pack(fill="x", padx=10, pady=5)
        text_box.insert("1.0", request[5])
        text_box.configure(state="disabled")
        
        if employee_response:
            response_label = ctk.CTkLabel(main_frame, text="💬 Ответ сотрудника:", anchor="w", font=ctk.CTkFont(weight="bold"))
            response_label.pack(anchor="w", padx=10, pady=(20, 5))
            
            response_box = ctk.CTkTextbox(main_frame, height=80, wrap="word")
            response_box.pack(fill="x", padx=10, pady=5)
            response_box.insert("1.0", employee_response)
            response_box.configure(state="disabled")
        
        self.response_text = None
        if status == 'in_progress':
            response_label = ctk.CTkLabel(main_frame, text="✍️ Ваш ответ:", anchor="w", font=ctk.CTkFont(weight="bold"))
            response_label.pack(anchor="w", padx=10, pady=(20, 5))
            
            self.response_text = ctk.CTkTextbox(main_frame, height=80, wrap="word")
            self.response_text.pack(fill="x", padx=10, pady=5)
            if employee_response:
                self.response_text.insert("1.0", employee_response)
        
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=10, pady=(20, 0))
        
        if status != 'completed' and status != 'redirected':
            redirect_btn = ctk.CTkButton(
                button_frame,
                text="🔄 Перенаправить",
                command=lambda: self.show_redirect_dialog(request_id, current_department, dialog),
                width=150,
                height=40,
                fg_color="#ffc107",
                hover_color="#e0a800",
                text_color="black"
            )
            redirect_btn.pack(side="left", padx=5)
        
        if status == 'pending':
            accept_btn = ctk.CTkButton(
                button_frame,
                text="✅ Принять",
                command=lambda: self.accept_request(request_id, dialog),
                width=150,
                height=40,
                fg_color="#28a745",
                hover_color="#218838"
            )
            accept_btn.pack(side="left", padx=5)
            
        elif status == 'in_progress':
            complete_btn = ctk.CTkButton(
                button_frame,
                text="🎯 Завершить",
                command=lambda: self.complete_request(request_id, dialog),
                width=150,
                height=40,
                fg_color="#007bff",
                hover_color="#0056b3"
            )
            complete_btn.pack(side="left", padx=5)
        
        close_btn = ctk.CTkButton(
            button_frame,
            text="✖ Закрыть",
            command=dialog.destroy,
            width=150,
            height=40,
            fg_color="#6c757d",
            hover_color="#5a6268"
        )
        close_btn.pack(side="left", padx=5)
    
    def show_redirect_dialog(self, request_id, current_dept, parent_dialog):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Перенаправление заявки")
        dialog.geometry("400x350")
        dialog.attributes('-topmost', True)
        dialog.grab_set()
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        title = ctk.CTkLabel(
            main_frame,
            text="🔄 Перенаправить заявку",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(pady=(10, 20))
        
        info = ctk.CTkLabel(
            main_frame,
            text=f"Заявка #{request_id}\nТекущий отдел: {self.get_dept_name(current_dept)}",
            font=ctk.CTkFont(size=14)
        )
        info.pack(pady=10)
        
        dept_label = ctk.CTkLabel(
            main_frame,
            text="Выберите новый отдел:",
            font=ctk.CTkFont(size=14)
        )
        dept_label.pack(pady=(20, 5))
        
        dept_var = tk.StringVar()
        dept_combo = ctk.CTkComboBox(
            main_frame,
            values=["Юридический", "Технический", "Делопроизводство"],
            variable=dept_var,
            width=250,
            height=40
        )
        dept_combo.pack(pady=10)
        dept_combo.set("Выберите отдел")
        
        comment_label = ctk.CTkLabel(
            main_frame,
            text="Комментарий (почему перенаправляете):",
            font=ctk.CTkFont(size=12)
        )
        comment_label.pack(pady=(10, 5))
        
        comment_text = ctk.CTkTextbox(main_frame, height=60, wrap="word")
        comment_text.pack(fill="x", padx=10, pady=5)
        
        def redirect():
            new_dept = dept_var.get()
            comment = comment_text.get("1.0", "end-1c").strip()
            
            dept_map = {
                "Юридический": "legal",
                "Технический": "technical",
                "Делопроизводство": "accounting"
            }
            
            new_dept_code = dept_map.get(new_dept)
            if not new_dept_code:
                messagebox.showerror("Ошибка", "Выберите отдел")
                return
            
            if new_dept_code == current_dept:
                messagebox.showerror("Ошибка", "Нельзя перенаправить в тот же отдел")
                return
            
            try:
                conn = self.get_pg_connection()
                cursor = conn.cursor()
                
                # Получаем данные заявки
                cursor.execute("""
                    SELECT full_name, organization, request_text 
                    FROM service_request 
                    WHERE id = %s
                """, (request_id,))
                
                request_data = cursor.fetchone()
                
                if not request_data:
                    messagebox.showerror("Ошибка", "Заявка не найдена")
                    conn.close()
                    return
                
                full_name, organization, request_text = request_data
                
                # Обновляем статус и отдел
                cursor.execute("""
                    UPDATE service_request 
                    SET department = %s, status = 'pending', employee_response = %s
                    WHERE id = %s
                """, (new_dept_code, f"[ПЕРЕНАПРАВЛЕНО из {self.get_dept_name(current_dept)}] {comment}", request_id))
                
                conn.commit()
                
                # Получаем email сотрудников нового отдела
                cursor.execute("""
                    SELECT employee_name, email 
                    FROM access_keys 
                    WHERE department = %s AND is_active = TRUE
                """, (new_dept_code,))
                
                new_employees = cursor.fetchall()
                conn.close()
                
                # Отправляем уведомления сотрудникам нового отдела
                for emp_name, emp_email in new_employees:
                    self.send_employee_notification(
                        emp_email,
                        emp_name,
                        new_dept_code,
                        {
                            'id': request_id,
                            'full_name': full_name,
                            'organization': organization,
                            'request_text': request_text,
                            'comment': f"Перенаправлено из {self.get_dept_name(current_dept)}. {comment}"
                        }
                    )
                
                # Уведомление клиенту
                self.send_client_notification(
                    request_id,
                    'redirected',
                    f"Перенаправлено в {self.get_dept_name(new_dept_code)}. {comment}"
                )
                
                self.show_notification(
                    "🔄 Заявка перенаправлена", 
                    f"Заявка #{request_id} отправлена в {new_dept}"
                )
                
                parent_dialog.destroy()
                dialog.destroy()
                self.root.after(500, self.load_data)
                
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
        
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", pady=20)
        
        redirect_btn = ctk.CTkButton(
            btn_frame,
            text="✅ Перенаправить",
            command=redirect,
            width=150,
            height=40,
            fg_color="#ffc107",
            text_color="black"
        )
        redirect_btn.pack(side="left", padx=5)
        
        cancel_btn = ctk.CTkButton(
            btn_frame,
            text="✖ Отмена",
            command=dialog.destroy,
            width=150,
            height=40
        )
        cancel_btn.pack(side="left", padx=5)
    
    def get_dept_name(self, dept_code):
        dept_map = {
            'legal': 'Юридический',
            'technical': 'Технический',
            'accounting': 'Делопроизводство'
        }
        return dept_map.get(dept_code, dept_code)
    
    def accept_request(self, request_id, dialog):
        try:
            conn = self.get_pg_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE service_request 
                SET status = 'in_progress' 
                WHERE id = %s
            """, (request_id,))
            
            conn.commit()
            conn.close()
            
            self.send_client_notification(request_id, 'in_progress')
            
            self.show_notification("✅ Заявка принята", f"Заявка #{request_id} принята в работу")
            dialog.destroy()
            self.root.after(500, self.load_data)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", f"Не удалось принять заявку: {e}")
    
    def complete_request(self, request_id, dialog):
        try:
            response_text = ""
            if hasattr(self, 'response_text') and self.response_text:
                response_text = self.response_text.get("1.0", "end-1c").strip()
            
            conn = self.get_pg_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE service_request 
                SET status = 'completed', employee_response = %s, completed_at = %s
                WHERE id = %s
            """, (response_text, datetime.now(), request_id))
            
            conn.commit()
            conn.close()
            
            self.send_client_notification(request_id, 'completed', response_text)
            
            self.show_notification("✅ Заявка завершена", f"Заявка #{request_id} завершена")
            dialog.destroy()
            self.root.after(500, self.load_data)
            
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            messagebox.showerror("Ошибка", f"Не удалось завершить заявку: {e}")
    
    def send_employee_notification(self, email, name, department, request_data):
        try:
            import smtplib
            import ssl
            from email.mime.text import MIMEText
            
            dept_names = {
                'legal': 'Юридический',
                'technical': 'Технический',
                'accounting': 'Делопроизводство'
            }
            dept_name = dept_names.get(department, department)
            
            if 'Перенаправлено' in request_data.get('comment', ''):
                subject = f"🔄 Заявка #{request_data['id']} перенаправлена в ваш отдел"
            else:
                subject = f"🔔 Новая заявка #{request_data['id']} в {dept_name} отдел"
            
            message = f"""
            Уважаемый {name}!
            
            {'Вам перенаправлена' if 'Перенаправлено' in request_data.get('comment', '') else 'В ваш отдел поступила'} заявка:
            
            📋 Номер заявки: {request_data['id']}
            👤 Клиент: {request_data['full_name']}
            🏢 Организация: {request_data['organization']}
            
            📝 Текст заявки:
            {request_data['request_text']}
            
            💬 Комментарий: {request_data.get('comment', 'Без комментария')}
            
            Для обработки заявки откройте приложение "Конфигуратор".
            
            С уважением,
            Единая система платежей
            """
            
            sender = "esp.notificator@gmail.com"
            password = "rxzo okqz mvsl luyo"
            
            for port in [465, 587, 25]:
                try:
                    print(f"📧 Отправка {name} через порт {port}")
                    
                    context = ssl.create_default_context()
                    msg = MIMEText(message, 'plain', 'utf-8')
                    msg['Subject'] = subject
                    msg['From'] = sender
                    msg['To'] = email
                    
                    if port == 465:
                        server = smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=30, context=context)
                    else:
                        server = smtplib.SMTP("smtp.gmail.com", port, timeout=30)
                        server.starttls(context=context)
                    
                    server.login(sender, password)
                    server.send_message(msg)
                    server.quit()
                    
                    print(f"✅ Уведомление отправлено {name}")
                    return True
                    
                except Exception as e:
                    print(f"❌ Порт {port} не работает: {e}")
                    continue
            
            return False
            
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False
    
    def send_client_notification(self, request_id, status, comment=""):
        try:
            import requests
            import urllib3
            # Отключаем warnings про SSL
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            
            response = requests.post(
                f'{API_BASE_URL}/api/notify-client/',
                json={
                    'request_id': request_id,
                    'status': status,
                    'comment': comment
                },
                timeout=5,
                verify=False  # ВРЕМЕННО отключаем проверку SSL
            )
            if response.status_code == 200:
                print(f"📧 Уведомление клиенту о заявке #{request_id} отправлено")
                return True
            else:
                print(f"⚠️ Ошибка API: {response.status_code}")
                print(f"Ответ: {response.text}")
                return False
        except Exception as e:
            print(f"⚠️ Ошибка уведомления клиента: {e}")
            return False

    def check_for_new_requests(self):
        try:
            conn = self.get_pg_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, full_name, organization, department, request_text, created_at
                FROM service_request 
                WHERE status = 'pending' AND department = %s
                ORDER BY created_at DESC
            """, (self.employee['department'],))
            
            new_requests = cursor.fetchall()
            
            cursor.execute("""
                SELECT COUNT(*) FROM service_request 
                WHERE status = 'pending' AND department = %s
            """, (self.employee['department'],))
            total_new = cursor.fetchone()[0]
            
            conn.close()
            
            department_map = {
                'legal': 'Юридический',
                'technical': 'Технический',
                'accounting': 'Делопроизводство'
            }
            
            for req in new_requests:
                req_id, name, org, dept, text, created = req
                
                if req_id not in self.known_requests:
                    self.known_requests.add(req_id)
                    department = department_map.get(dept, dept)
                    
                    print(f"🔔 НОВАЯ ЗАЯВКА #{req_id}: {name} - {department}")
                    
                    if self.sound_enabled:
                        self.play_notification_sound()
                    
                    if self.notification_enabled:
                        self.show_notification(
                            f"📬 Новая заявка: {department}",
                            f"От: {name}\nОрганизация: {org}\n\n{text[:150]}..."
                        )
                    
                    self.root.after(0, self.load_data)

            self.root.after(0, lambda: self.counter_label.configure(text=f"Новых: {total_new}"))
            return len(new_requests)
            
        except Exception as e:
            print(f"Ошибка проверки: {e}")
            return 0
    
    def auto_update(self):
        while self.running:
            try:
                new_count = self.check_for_new_requests()
                if new_count > 0:
                    self.root.after(0, self.load_data)
                    self.root.after(0, lambda: self.status_label.configure(
                        text=f"Активно • Отдел: {self.get_department_name()} • Новых: {new_count}"
                    ))
                
            except Exception as e:
                print(f"Ошибка автообновления: {e}")
            time.sleep(10)
    
    def start_auto_monitoring(self):
        thread = threading.Thread(target=self.auto_update, daemon=True)
        thread.start()
        print("Автоматический мониторинг запущен (каждые 10 секунд)")
    
    def open_website(self):
        import webbrowser
        webbrowser.open(API_BASE_URL)
    
    def show_statistics(self):
        try:
            conn = self.get_pg_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT COUNT(*) FROM service_request WHERE department = %s
            """, (self.employee['department'],))
            total = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT COUNT(*) FROM service_request 
                WHERE status = 'pending' AND department = %s
            """, (self.employee['department'],))
            new = cursor.fetchone()[0]
            
            cursor.execute("""
                SELECT status, COUNT(*) FROM service_request 
                WHERE department = %s GROUP BY status
            """, (self.employee['department'],))
            by_status = cursor.fetchall()
            
            conn.close()
            
            stats = f"""📊 СТАТИСТИКА ПО ОТДЕЛУ {self.get_department_name()}

Всего заявок: {total}
Новых заявок: {new}

По статусам:"""
            
            status_map = {
                'pending': '🟡 Ожидает',
                'in_progress': '🟠 В работе',
                'completed': '🟢 Завершено',
                'redirected': '🔄 Перенаправлено'
            }
            
            for status, count in by_status:
                stats += f"\n{status_map.get(status, status)}: {count}"
            
            messagebox.showinfo("Статистика", stats)
            
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
    
    def show_settings(self):
        settings_window = ctk.CTkToplevel(self.root)
        settings_window.title("Настройки")
        settings_window.geometry("400x350")
        settings_window.lift()
        settings_window.focus_force()
        
        ctk.CTkLabel(settings_window, text="⚙ Настройки уведомлений", 
                    font=ctk.CTkFont(size=18, weight="bold")).pack(pady=20)
        
        ctk.CTkLabel(settings_window, text=f"Сотрудник: {self.employee['full_name']}", 
                    font=ctk.CTkFont(size=14)).pack(pady=5)
        
        ctk.CTkLabel(settings_window, text=f"Отдел: {self.get_department_name()}", 
                    font=ctk.CTkFont(size=14)).pack(pady=5)
        
        ctk.CTkLabel(settings_window, text=f"Ключ доступа: {self.employee['access_key']}", 
                    font=ctk.CTkFont(size=12)).pack(pady=5)
        
        self.notification_var = tk.BooleanVar(value=self.notification_enabled)
        notification_check = ctk.CTkCheckBox(
            settings_window,
            text="Включить уведомления",
            variable=self.notification_var,
            command=lambda: setattr(self, 'notification_enabled', self.notification_var.get())
        )
        notification_check.pack(pady=10)
        
        self.sound_var = tk.BooleanVar(value=self.sound_enabled)
        sound_check = ctk.CTkCheckBox(
            settings_window,
            text="Включить звук",
            variable=self.sound_var,
            command=lambda: setattr(self, 'sound_enabled', self.sound_var.get())
        )
        sound_check.pack(pady=10)
        
        def test_notification():
            if self.sound_enabled:
                self.play_notification_sound()
            self.show_notification(
                "✅ Тестовое уведомление",
                f"Привет, {self.employee['full_name']}!"
            )
        
        ctk.CTkButton(
            settings_window,
            text="🔊 Проверить уведомление",
            command=test_notification
        ).pack(pady=10)
        
        ctk.CTkButton(settings_window, text="Сохранить", command=settings_window.destroy).pack(pady=10)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    def start_app(employee):
        app = ModernDesktopNotificator(employee)
        app.run()
    
    login = LoginWindow(start_app)
    login.run()