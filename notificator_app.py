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
import warnings

# Подавляем предупреждения Tkinter
warnings.filterwarnings("ignore", category=UserWarning, module="tkinter")

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
        self.root.state("zoomed")  # Во весь экран с рамками
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
        if hasattr(self, 'tray_icon'):
            self.tray_icon.stop()
        self.root.quit()
        sys.exit(0)
    
    def setup_ui(self):
        # Верхняя панель
        top_frame = ctk.CTkFrame(self.root, height=60, corner_radius=0, fg_color="#1a1a1a")
        top_frame.pack(fill="x", padx=0, pady=0)
        
        title = ctk.CTkLabel(
            top_frame,
            text=f"📬 Конфигуратор - {self.employee['full_name']} ({self.get_department_name()})",
            font=ctk.CTkFont(size=18, weight="bold")
        )
        title.pack(side="left", padx=20, pady=15)
        
        # Кнопки в топбаре
        btn_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        btn_frame.pack(side="right", padx=20)
        
        buttons = [
            ("🌐 Сайт", self.open_website),
            ("📊 Статистика", self.show_statistics),
            ("⚙ Настройки", self.show_settings),
        ]
        
        for text, cmd in buttons:
            ctk.CTkButton(
                btn_frame,
                text=text,
                command=cmd,
                width=100,
                height=35
            ).pack(side="left", padx=5)
        
        # Вкладки
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
        
        # Основная область с таблицей
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Canvas для скролла
        canvas = tk.Canvas(main_frame, highlightthickness=0, bg='#2b2b2b')
        scrollbar = ctk.CTkScrollbar(main_frame, orientation="vertical", command=canvas.yview)
        self.scrollable_frame = ctk.CTkFrame(canvas, fg_color="transparent")
        
        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Нижняя панель статуса
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
    
    def switch_tab(self, tab):
        self.current_tab = tab
        if tab == "active":
            self.active_tab_btn.configure(fg_color="#007bff")
            self.archive_tab_btn.configure(fg_color="#2b2b2b")
        else:
            self.active_tab_btn.configure(fg_color="#2b2b2b")
            self.archive_tab_btn.configure(fg_color="#6c757d")
        self.load_data()
    
    def load_data(self):
        """Загрузка и отображение заявок"""
        try:
            # Очищаем контейнер
            for widget in self.scrollable_frame.winfo_children():
                widget.destroy()
            
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
            
            # Если нет заявок
            if not requests:
                no_data_label = ctk.CTkLabel(
                    self.scrollable_frame,
                    text="📭 Нет заявок",
                    font=ctk.CTkFont(size=16)
                )
                no_data_label.pack(pady=50)
                return
                
            # ========== ЗАГОЛОВКИ ==========
            headers_frame = ctk.CTkFrame(self.scrollable_frame, fg_color="#1f1f1f", height=40)
            headers_frame.pack(fill="x", pady=(0, 5))
            
            # Заголовки
            ctk.CTkLabel(headers_frame, text="  ", width=30).pack(side="left")
            ctk.CTkLabel(headers_frame, text="ID", width=50, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(headers_frame, text="Дата", width=130, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(headers_frame, text="ФИО", width=200, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(headers_frame, text="Организация", width=130, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(headers_frame, text="Отдел", width=120, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            ctk.CTkLabel(headers_frame, text="Статус", width=100, anchor="w", font=ctk.CTkFont(weight="bold")).pack(side="left")
            
            # ========== ЗАЯВКИ ==========
            department_map = {
                'legal': 'Юридический',
                'technical': 'Технический',
                'accounting': 'Делопроизводство'
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
                    height=40
                )
                row_frame.pack(fill="x", pady=1)
                row_frame.pack_propagate(False)
                
                # Статус-индикатор
                status_color = "#dc3545" if status == 'pending' else "#ffc107" if status == 'in_progress' else "#28a745"
                ctk.CTkLabel(
                    row_frame,
                    text="●",
                    text_color=status_color,
                    font=ctk.CTkFont(size=14),
                    width=30
                ).pack(side="left", padx=(10, 0))
                
                # Преобразуем datetime в строку
                date_str = created.strftime("%d.%m.%Y %H:%M") if created else ""
                
                # Исправляем ФИО если слиплось с организацией
                display_name = full_name if full_name else ""
                if display_name and org and org in display_name:
                    display_name = display_name.replace(org, "").strip()
                
                # Данные
                ctk.CTkLabel(row_frame, text=str(req_id), width=50, anchor="w").pack(side="left")
                ctk.CTkLabel(row_frame, text=date_str, width=130, anchor="w").pack(side="left")
                ctk.CTkLabel(row_frame, text=display_name, width=200, anchor="w").pack(side="left")
                ctk.CTkLabel(row_frame, text=org if org else "", width=130, anchor="w").pack(side="left")
                ctk.CTkLabel(row_frame, text=department_map.get(dept, dept), width=120, anchor="w").pack(side="left")
                ctk.CTkLabel(row_frame, text=status_names.get(status, status), width=100, anchor="w").pack(side="left")
                
                # Клик
                row_frame.bind("<Button-1>", lambda e, r=req: self.show_request_details(r))
                for child in row_frame.winfo_children():
                    child.bind("<Button-1>", lambda e, r=req: self.show_request_details(r))
                    
        except Exception as e:
            print(f"❌ Ошибка загрузки: {e}")
            import traceback
            traceback.print_exc()
    
    def show_request_details(self, request):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title(f"Заявка #{request[0]}")
        dialog.geometry("800x800")
        dialog.attributes('-topmost', True)
        
        main_frame = ctk.CTkFrame(dialog)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        department_map = {
            'legal': 'Юридический',
            'technical': 'Технический',
            'accounting': 'Делопроизводство'
        }
        
        status_names = {
            'pending': '🟡 Ожидает рассмотрения',
            'in_progress': '🟠 Принята в работу',
            'completed': '🟢 Завершена',
            'redirected': '🔄 Перенаправлена'
        }
        
        # Информация
        info_text = f"""
ID: {request[0]}
Дата: {request[1]}
ФИО: {request[2]}
Организация: {request[3]}
Отдел: {department_map.get(request[4], request[4])}
Статус: {status_names.get(request[6], request[6])}
        """
        
        info_label = ctk.CTkLabel(
            main_frame,
            text=info_text,
            font=ctk.CTkFont(size=14),
            justify="left"
        )
        info_label.pack(anchor="w", pady=10)
        
        # Текст заявки
        text_label = ctk.CTkLabel(
            main_frame,
            text="📝 Текст заявки:",
            font=ctk.CTkFont(size=14, weight="bold")
        )
        text_label.pack(anchor="w", pady=(20, 5))
        
        text_box = ctk.CTkTextbox(main_frame, height=150, wrap="word")
        text_box.pack(fill="x", pady=5)
        text_box.insert("1.0", request[5])
        text_box.configure(state="disabled")
        
        # Ответ сотрудника
        if request[7]:
            resp_label = ctk.CTkLabel(
                main_frame,
                text="💬 Ответ сотрудника:",
                font=ctk.CTkFont(size=14, weight="bold")
            )
            resp_label.pack(anchor="w", pady=(20, 5))
            
            resp_box = ctk.CTkTextbox(main_frame, height=100, wrap="word")
            resp_box.pack(fill="x", pady=5)
            resp_box.insert("1.0", request[7])
            resp_box.configure(state="disabled")
        
        # Кнопки
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(pady=20)
        
        # Кнопка перенаправления для всех незавершенных заявок
        if request[6] != 'completed':
            ctk.CTkButton(
                btn_frame,
                text="🔄 Перенаправить",
                command=lambda: self.redirect_request(request[0], request[4], dialog),
                width=150,
                height=40,
                fg_color="#ffc107",
                hover_color="#e0a800",
                text_color="black"
            ).pack(side="left", padx=5)
        
        if request[6] == 'pending':
            ctk.CTkButton(
                btn_frame,
                text="✅ Принять в работу",
                command=lambda: self.accept_request(request[0], dialog),
                width=150,
                height=40,
                fg_color="#28a745"
            ).pack(side="left", padx=5)
        
        elif request[6] == 'in_progress':
            ctk.CTkButton(
                btn_frame,
                text="🎯 Завершить",
                command=lambda: self.complete_request(request[0], dialog),
                width=150,
                height=40,
                fg_color="#007bff"
            ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="✖ Закрыть",
            command=dialog.destroy,
            width=150,
            height=40,
            fg_color="#6c757d"
        ).pack(side="left", padx=5)
    
    def redirect_request(self, request_id, current_dept, parent_dialog):
        dialog = ctk.CTkToplevel(self.root)
        dialog.title("Перенаправление заявки")
        dialog.geometry("400x400")
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
            text="Комментарий:",
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
                
                cursor.execute("""
                    UPDATE service_request 
                    SET department = %s, 
                        status = 'pending',
                        employee_response = %s
                    WHERE id = %s
                """, (new_dept_code, f"[ПЕРЕНАПРАВЛЕНО из {self.get_dept_name(current_dept)}] {comment}", request_id))
                
                conn.commit()
                conn.close()
                
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
        
        ctk.CTkButton(
            btn_frame,
            text="✅ Перенаправить",
            command=redirect,
            width=150,
            height=40,
            fg_color="#ffc107",
            text_color="black"
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            btn_frame,
            text="✖ Отмена",
            command=dialog.destroy,
            width=150,
            height=40
        ).pack(side="left", padx=5)
    
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
            messagebox.showerror("Ошибка", str(e))
    
    def complete_request(self, request_id, dialog):
        # Создаем диалог для ответа
        response_dialog = ctk.CTkToplevel(dialog)
        response_dialog.title("Ответ клиенту")
        response_dialog.geometry("500x400")
        response_dialog.lift()
        response_dialog.focus_force()
        response_dialog.attributes('-topmost', True)
        response_dialog.grab_set()
        
        ctk.CTkLabel(
            response_dialog,
            text="✍️ Напишите ответ клиенту:",
            font=ctk.CTkFont(size=16, weight="bold")
        ).pack(pady=20)
        
        response_text = ctk.CTkTextbox(response_dialog, height=200)
        response_text.pack(fill="both", expand=True, padx=20, pady=10)
        
        def submit_response():
            text = response_text.get("1.0", "end-1c").strip()
            
            try:
                conn = self.get_pg_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE service_request 
                    SET status = 'completed', 
                        employee_response = %s,
                        completed_at = %s
                    WHERE id = %s
                """, (text, datetime.now(), request_id))
                
                conn.commit()
                conn.close()
                
                self.send_client_notification(request_id, 'completed', text)
                
                self.show_notification("✅ Заявка завершена", f"Заявка #{request_id} завершена")
                response_dialog.destroy()
                dialog.destroy()
                self.root.after(500, self.load_data)
                
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))
        
        ctk.CTkButton(
            response_dialog,
            text="✅ Отправить",
            command=submit_response,
            width=200,
            height=40
        ).pack(pady=20)
    
    def send_client_notification(self, request_id, status, comment=""):
        try:
            import requests
            response = requests.post(
                f'{API_BASE_URL}/api/notify-client/',
                json={
                    'request_id': request_id,
                    'status': status,
                    'comment': comment
                },
                timeout=5
            )
            if response.status_code == 200:
                print(f"📧 Уведомление клиенту о заявке #{request_id} отправлено")
                return True
            else:
                print(f"⚠️ Ошибка API: {response.status_code}")
                return False
        except Exception as e:
            print(f"⚠️ Ошибка уведомления клиента: {e}")
            return False
    
    def check_for_new_requests(self):
        try:
            conn = self.get_pg_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, full_name, organization, department, request_text
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
                req_id, name, org, dept, text = req
                
                if req_id not in self.known_requests:
                    self.known_requests.add(req_id)
                    department = department_map.get(dept, dept)
                    
                    print(f"🔔 НОВАЯ ЗАЯВКА #{req_id}")
                    
                    if self.sound_enabled:
                        self.play_notification_sound()
                    
                    if self.notification_enabled:
                        self.show_notification(
                            f"📬 Новая заявка: {department}",
                            f"От: {name}\nОрганизация: {org}"
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
        settings_window.attributes('-topmost', True)
        
        ctk.CTkLabel(
            settings_window,
            text="⚙ Настройки уведомлений",
            font=ctk.CTkFont(size=18, weight="bold")
        ).pack(pady=20)
        
        ctk.CTkLabel(
            settings_window,
            text=f"Сотрудник: {self.employee['full_name']}",
            font=ctk.CTkFont(size=14)
        ).pack(pady=5)
        
        ctk.CTkLabel(
            settings_window,
            text=f"Отдел: {self.get_department_name()}",
            font=ctk.CTkFont(size=14)
        ).pack(pady=5)
        
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
        
        ctk.CTkButton(
            settings_window,
            text="Сохранить",
            command=settings_window.destroy
        ).pack(pady=10)
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    def start_app(employee):
        app = ModernDesktopNotificator(employee)
        app.run()
    
    login = LoginWindow(start_app)
    login.run()