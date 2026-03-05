from django.shortcuts import render, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.conf import settings
from .models import ServiceRequest, Employee, RegisterUser
from .email_utils import send_employee_notification, send_client_notification
import json
import sqlite3
import os

def index(request):
    """Главная страница с кнопками входа/регистрации"""
    return render(request, 'requests_app/index.html')

def register_page(request):
    if request.method == 'POST':
        first_name = request.POST.get('first_name')
        middle_name = request.POST.get('middle_name', '')
        last_name = request.POST.get('last_name')
        
        # Формируем полное ФИО для обратной совместимости
        full_name = f"{last_name} {first_name} {middle_name}".strip()
        
        user = RegisterUser.objects.using('users_db').create(
            first_name=first_name,
            middle_name=middle_name,
            last_name=last_name,
            full_name=full_name,  # сохраняем, но не используем в приветствии
            phone=request.POST.get('phone'),
            email=request.POST.get('email'),
            payment_id=request.POST.get('payment_id', ''),
            login=request.POST.get('username'),
            password=request.POST.get('password1')
        )
        # ... остальной код
        print(f"✅ Юзер сохранен в Register_Users.sqlite3: {user.full_name}")
        
        # Создаем сессию
        request.session['user_login'] = user.login
        request.session['user_name'] = user.full_name
        
        return redirect('registration_success')
    
    return render(request, 'requests_app/register.html')

def login_page(request):
    """Вход - проверяем в Register_Users.sqlite3"""
    if request.method == 'POST':
        login_input = request.POST.get('username')
        password = request.POST.get('password')
        
        try:
            user = RegisterUser.objects.using('users_db').get(
                login=login_input,
                password=password
            )
            request.session['user_login'] = user.login
            request.session['user_name'] = user.full_name
            return redirect('cabinet')
        except RegisterUser.DoesNotExist:
            return render(request, 'requests_app/login.html', {'error': 'Неверный логин или пароль'})
    
    return render(request, 'requests_app/login.html')

def logout_view(request):
    """Выход"""
    request.session.flush()
    return redirect('index')

def registration_success(request):
    """Страница успешной регистрации"""
    return render(request, 'requests_app/registration_success.html')

def cabinet(request):
    """Личный кабинет"""
    user_login = request.session.get('user_login')
    if not user_login:
        return redirect('login_page')
    
    try:
        user = RegisterUser.objects.using('users_db').get(login=user_login)
    except RegisterUser.DoesNotExist:
        return redirect('login_page')
    
    # Заявки берем из notificator_data.sqlite3
    requests_list = ServiceRequest.objects.filter(full_name=user.full_name).order_by('-created_at')
    
    context = {
        'user': user,
        'requests': requests_list,
    }
    return render(request, 'requests_app/cabinet.html', context)

def submit_request(request):
    """Отправка заявки в notificator_data.sqlite3"""
    if request.method == 'POST':
        # Проверяем что юзер залогинен
        if 'user_login' not in request.session:
            return JsonResponse({'status': 'error', 'message': 'Не авторизован'}, status=401)
        
        # Получаем данные юзера из сессии
        user_login = request.session.get('user_login')
        user = RegisterUser.objects.using('users_db').get(login=user_login)
        
        # Создаем заявку
        service_request = ServiceRequest.objects.create(
            full_name=user.full_name,
            organization=request.POST.get('organization'),
            department=request.POST.get('department'),
            payment_doc=request.POST.get('payment_doc', ''),
            request_text=request.POST.get('request_text'),
            status='pending'
        )
        
        print(f"✅ Заявка #{service_request.id} создана, отдел: {service_request.department}")
        
        # ==== ОТПРАВКА УВЕДОМЛЕНИЙ ====
        try:
            # Отправка клиенту
            send_client_notification(
                client_email=user.email,
                client_name=user.full_name,
                request_id=service_request.id,
                status='pending'
            )
            print(f"📧 Уведомление клиенту отправлено на {user.email}")
            
            # Отправка сотрудникам
            keys_db_path = os.path.join(settings.BASE_DIR, 'Access_data.sqlite3')
            conn = sqlite3.connect(keys_db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT employee_name, email 
                FROM access_keys 
                WHERE department = ? AND is_active = 1 AND email IS NOT NULL
            """, (service_request.department,))
            
            employees = cursor.fetchall()
            conn.close()
            
            print(f"📧 Найдено сотрудников в отделе {service_request.department}: {len(employees)}")
            
            request_data = {
                'id': service_request.id,
                'full_name': service_request.full_name,
                'organization': service_request.organization,
                'request_text': service_request.request_text
            }
            
            for emp_name, emp_email in employees:
                send_employee_notification(
                    employee_email=emp_email,
                    employee_name=emp_name,
                    department=service_request.department,
                    request_data=request_data
                )
                print(f"📨 Уведомление отправлено {emp_name} ({emp_email})")
                
        except Exception as e:
            print(f"⚠️ Ошибка при отправке уведомлений: {e}")
            import traceback
            traceback.print_exc()
        # ==== КОНЕЦ ОТПРАВКИ ====
        
        return JsonResponse({'status': 'success', 'message': 'Заявка успешно отправлена!'})
    
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def notify_client_from_app(request):
    """API для отправки уведомлений клиенту из приложения"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            request_id = data.get('request_id')
            status = data.get('status')
            comment = data.get('comment', '')
            
            # Получаем заявку
            service_request = ServiceRequest.objects.get(id=request_id)
            
            # Получаем email клиента из Register_Users
            user = RegisterUser.objects.using('users_db').filter(full_name=service_request.full_name).first()
            
            if user and user.email:
                send_client_notification(
                    client_email=user.email,
                    client_name=user.full_name,
                    request_id=request_id,
                    status=status,
                    comment=comment
                )
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'status': 'error', 'message': 'Email клиента не найден'})
                
        except ServiceRequest.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Заявка не найдена'}, status=404)
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error'}, status=400)

# API для приложения сотрудников
@csrf_exempt
def employee_login(request):
    """Вход сотрудника в приложение"""
    if request.method == 'POST':
        data = json.loads(request.body)
        username = data.get('username')
        password = data.get('password')
        
        try:
            employee = Employee.objects.get(username=username, password=password, is_active=True)
            return JsonResponse({
                'status': 'success',
                'employee': {
                    'id': employee.id,
                    'full_name': employee.full_name,
                    'department': employee.department
                }
            })
        except Employee.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Неверные данные'}, status=401)
    
    return JsonResponse({'status': 'error'}, status=400)

@csrf_exempt
def get_employee_requests(request):
    """Получение заявок для сотрудника (по его отделу)"""
    if request.method == 'GET':
        department = request.GET.get('department')
        
        if department:
            requests_list = ServiceRequest.objects.filter(department=department).order_by('-created_at')
        else:
            requests_list = ServiceRequest.objects.all().order_by('-created_at')
        
        data = []
        for req in requests_list:
            data.append({
                'id': req.id,
                'full_name': req.full_name,
                'organization': req.organization,
                'department': req.get_department_display(),
                'request_text': req.request_text,
                'payment_doc': req.payment_doc,
                'status': req.status,
                'created_at': req.created_at.isoformat(),
            })
        
        return JsonResponse({'requests': data})
    
    return JsonResponse({'status': 'error'}, status=400)
@csrf_exempt
def notify_client_from_app(request):
    print(f"🔔 Получен запрос на /api/notify-client/ метод: {request.method}")
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"📦 Данные запроса: {data}")
            
            request_id = data.get('request_id')
            status = data.get('status')
            comment = data.get('comment', '')
            
            # Твой код отправки email
            from .email_utils import send_client_notification
            
            # Получаем заявку
            service_request = ServiceRequest.objects.get(id=request_id)
            print(f"📋 Заявка #{request_id} найдена")
            
            # Получаем пользователя
            user = RegisterUser.objects.using('users_db').filter(full_name=service_request.full_name).first()
            print(f"👤 Пользователь: {user}")
            
            if user and user.email:
                print(f"📧 Отправка email на {user.email}")
                result = send_client_notification(
                    client_email=user.email,
                    client_name=user.full_name,
                    request_id=request_id,
                    status=status,
                    comment=comment
                )
                print(f"✅ Результат отправки: {result}")
                return JsonResponse({'status': 'success', 'email_sent': result})
            else:
                print(f"❌ Email не найден для пользователя {service_request.full_name}")
                return JsonResponse({'status': 'error', 'message': 'Email не найден'})
                
        except ServiceRequest.DoesNotExist:
            print(f"❌ Заявка #{request_id} не найдена")
            return JsonResponse({'status': 'error', 'message': 'Заявка не найдена'}, status=404)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=400)