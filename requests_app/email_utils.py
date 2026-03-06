import smtplib
import ssl
import time
import socket
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# НАСТРОЙКИ GMAIL
SMTP_USER = "esp.notificator@gmail.com"
SMTP_PASSWORD = "rxzo okqz mvsl luyo"

def send_email(to_email, subject, message):
    """Отправка email с автоматическим выбором порта и повторными попытками"""
    
    ports_to_try = [465, 587, 25]
    
    for attempt in range(3):
        for port in ports_to_try:
            try:
                print(f"📧 Попытка {attempt+1}, порт {port} для {to_email}")
                
                msg = MIMEMultipart()
                msg['From'] = SMTP_USER
                msg['To'] = to_email
                msg['Subject'] = subject
                msg.attach(MIMEText(message, 'plain', 'utf-8'))
                
                context = ssl.create_default_context()
                
                if port == 465:
                    server = smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=30, context=context)
                else:
                    server = smtplib.SMTP("smtp.gmail.com", port, timeout=30)
                    server.starttls(context=context)
                
                server.login(SMTP_USER, SMTP_PASSWORD)
                server.send_message(msg)
                server.quit()
                
                print(f"✅ Email успешно отправлен на {to_email} через порт {port}")
                return True
                
            except socket.timeout:
                print(f"❌ Таймаут на порту {port}")
                continue
            except smtplib.SMTPAuthenticationError as e:
                print(f"❌ Ошибка аутентификации на порту {port}: {e}")
                continue
            except Exception as e:
                print(f"❌ Порт {port} не работает: {e}")
                continue
        
        print(f"⏱️ Пауза 3 секунды перед следующей попыткой...")
        time.sleep(3)
    
    print(f"❌ Все попытки отправки на {to_email} провалились")
    return False

def send_employee_notification(employee_email, employee_name, department, request_data, redirect_info=None):
    """Уведомление сотруднику о новой заявке или перенаправлении"""
    
    dept_names = {
        'legal': 'Юридический',
        'technical': 'Технический',
        'accounting': 'Делопроизводство'
    }
    dept_name = dept_names.get(department, department)
    
    if redirect_info:
        # Это перенаправленная заявка
        subject = f"🔄 Перенаправлена заявка №{request_data['id']} в {dept_name} отдел"
        message = f"""
        Уважаемый {employee_name}!
        
        Сотрудник {redirect_info['from_employee']} из отдела {redirect_info['from_department']} перенаправил в ваш отдел заявку:
        
        📋 Номер заявки: {request_data['id']}
        👤 Клиент: {request_data['full_name']}
        🏢 Организация: {request_data['organization']}
        
        📝 Текст заявки:
        {request_data['request_text']}
        
        💬 Комментарий: {redirect_info.get('comment', 'Без комментария')}
        
        Для обработки заявки откройте приложение "Конфигуратор".
        
        С уважением,
        Единая система платежей
        """
    else:
        # Новая заявка
        subject = f"🔔 Новая заявка №{request_data['id']} в {dept_name} отдел"
        message = f"""
        Уважаемый {employee_name}!
        
        В ваш отдел ({dept_name}) поступила новая заявка:
        
        📋 Номер заявки: {request_data['id']}
        👤 Клиент: {request_data['full_name']}
        🏢 Организация: {request_data['organization']}
        
        📝 Текст заявки:
        {request_data['request_text']}
        
        Для обработки заявки откройте приложение "Конфигуратор".
        
        С уважением,
        Единая система платежей
        """
    
    return send_email(employee_email, subject, message)

def send_client_notification(client_email, client_name, request_id, status, comment=""):
    """Уведомление клиенту о статусе заявки"""
    
    status_text = {
        'pending': 'создана',
        'in_progress': 'принята в работу',
        'redirected': 'перенаправлена',
        'completed': 'завершена'
    }
    
    status_emoji = {
        'pending': '✅',
        'in_progress': '🟠',
        'redirected': '🔄',
        'completed': '✅'
    }
    
    status_messages = {
        'pending': f"""
        Ваша заявка №{request_id} успешно создана и передана в работу.
        Срок рассмотрения: до 3 рабочих дней.
        
        Вы можете отслеживать статус заявки в личном кабинете.
        """,
        
        'in_progress': f"""
        Ваша заявка №{request_id} принята в работу сотрудником нашего отдела.
        
        Вы можете отслеживать статус заявки в личном кабинете.
        """,
        
        'redirected': f"""
        Ваша заявка №{request_id} перенаправлена в профильный отдел для более качественного рассмотрения.
        
        Комментарий: {comment if comment else 'Перенаправлено по компетенции'}
        
        Вы можете отслеживать статус заявки в личном кабинете.
        """,
        
        'completed': f"""
        Ваша заявка №{request_id} выполнена.
        
        Ответ сотрудника:
        {comment if comment else 'Заявка обработана'}
        
        Спасибо за обращение!
        """
    }
    
    subject = f"{status_emoji.get(status, '📬')} Заявка №{request_id} {status_text.get(status, 'обновлена')}"
    
    message = f"""
    Уважаемый {client_name}!
    
    {status_messages.get(status, 'Статус вашей заявки обновлен.')}
    
    С уважением,
    Единая система платежей
    """
    
    return send_email(client_email, subject, message)

def test_connection():
    """Тест подключения к Gmail SMTP"""
    print("🔍 Тестирование подключения к Gmail SMTP...")
    print("=" * 50)
    
    working_ports = []
    
    for port in [465, 587, 25]:
        try:
            print(f"\n📡 Проверка порта {port}...")
            
            if port == 465:
                context = ssl.create_default_context()
                server = smtplib.SMTP_SSL("smtp.gmail.com", port, timeout=10, context=context)
            else:
                server = smtplib.SMTP("smtp.gmail.com", port, timeout=10)
                server.starttls()
            
            server.quit()
            print(f"✅ Порт {port} доступен")
            working_ports.append(port)
            
        except socket.timeout:
            print(f"❌ Порт {port} недоступен: таймаут")
        except Exception as e:
            print(f"❌ Порт {port} недоступен: {e}")
    
    print("\n" + "=" * 50)
    if working_ports:
        print(f"✅ Рабочие порты: {working_ports}")
        return True
    else:
        print("❌ Нет доступных портов для Gmail SMTP")
        return False

if __name__ == "__main__":
    test_connection()