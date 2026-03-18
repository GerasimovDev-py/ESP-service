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
import threading

def index(request):
    """Главная страница с кнопками входа/регистрации"""
    return render(request, 'requests_app/index.html')

def register_page(request):
    """Регистрация нового пользователя"""
    print("🔵 register_page вызван, метод:", request.method)
    
    if request.method == 'POST':
        print("📦 POST данные:", request.POST)
        
        try:
            first_name = request.POST.get('first_name')
            middle_name = request.POST.get('middle_name', '')
            last_name = request.POST.get('last_name')
            
            """Формируем полное ФИО"""
            full_name = f"{last_name} {first_name} {middle_name}".strip()
            print(f"👤 Создание пользователя: {full_name}")
            
            """Проверяем обязательные поля"""
            if not all([first_name, last_name, request.POST.get('phone'), 
                       request.POST.get('email'), request.POST.get('username'), 
                       request.POST.get('password1')]):
                print("❌ Не все обязательные поля заполнены")
                return render(request, 'requests_app/register.html', {
                    'error': 'Заполните все обязательные поля'
                })
            
            """Проверяем пароли"""
            if request.POST.get('password1') != request.POST.get('password2'):
                print("❌ Пароли не совпадают")
                return render(request, 'requests_app/register.html', {
                    'error': 'Пароли не совпадают'
                })
            
            """Создаем пользователя"""
            user = RegisterUser.objects.using('users_db').create(
                first_name=first_name,
                middle_name=middle_name,
                last_name=last_name,
                full_name=full_name,
                phone=request.POST.get('phone'),
                email=request.POST.get('email'),
                payment_id=request.POST.get('payment_id', ''),
                login=request.POST.get('username'),
                password=request.POST.get('password1')
            )
            
            print(f"✅ Пользователь создан в БД users_db: {user.login}")
            
            """Создаем сессию"""
            request.session['user_login'] = user.login
            request.session['user_name'] = user.full_name
            request.session.save()
            
            print("🔄 Перенаправление на registration_success")
            return redirect('registration_success')
            
        except Exception as e:
            print(f"❌ ОШИБКА при регистрации: {e}")
            import traceback
            traceback.print_exc()
            return render(request, 'requests_app/register.html', {
                'error': f'Ошибка при регистрации: {str(e)}'
            })
    
    return render(request, 'requests_app/register.html')

def login_page(request):
    """Вход пользователя"""
    print(f"🔵 login_page вызван, метод: {request.method}")
    
    if request.method == 'POST':
        login_input = request.POST.get('username')
        password = request.POST.get('password')
        print(f"📦 Попытка входа: login={login_input}")
        
        try:
            user = RegisterUser.objects.using('users_db').get(
                login=login_input,
                password=password
            )
            print(f"✅ Пользователь найден: {user.full_name}")
            
            request.session['user_login'] = user.login
            request.session['user_name'] = user.full_name
            request.session.save()
            print(f"✅ Сессия создана: {request.session.get('user_login')}")
            
            return redirect('cabinet')
        except RegisterUser.DoesNotExist:
            print(f"❌ Пользователь не найден или неверный пароль")
            return render(request, 'requests_app/login.html', {'error': 'Неверный логин или пароль'})
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return render(request, 'requests_app/login.html', {'error': str(e)})
    
    return render(request, 'requests_app/login.html')

def logout_view(request):
    """Выход из системы"""
    request.session.flush()
    return redirect('index')

def registration_success(request):
    """Страница успешной регистрации"""
    return render(request, 'requests_app/registration_success.html')

def cabinet(request):
    """Личный кабинет пользователя"""
    print("🔵 cabinet view вызван")
    print(f"👤 Сессия user_login: {request.session.get('user_login')}")
    
    user_login = request.session.get('user_login')
    if not user_login:
        print("❌ Нет user_login в сессии, редирект на login")
        return redirect('login_page')
    
    try:
        print(f"🔍 Ищем пользователя с login={user_login} в users_db")
        user = RegisterUser.objects.using('users_db').get(login=user_login)
        print(f"✅ Пользователь найден: {user.full_name}")
    except RegisterUser.DoesNotExist:
        print(f"❌ Пользователь {user_login} не найден в БД")
        return redirect('login_page')
    except Exception as e:
        print(f"❌ Ошибка при поиске пользователя: {e}")
        import traceback
        traceback.print_exc()
        return redirect('login_page')
    
    # Заявки
    try:
        print(f"🔍 Ищем заявки для {user.full_name}")
        requests_list = ServiceRequest.objects.filter(full_name=user.full_name).order_by('-created_at')
        print(f"✅ Найдено заявок: {len(requests_list)}")
    except Exception as e:
        print(f"❌ Ошибка при загрузке заявок: {e}")
        requests_list = []
    
    context = {
        'user': user,
        'requests': requests_list,
    }
    print("✅ Рендерим cabinet.html")
    return render(request, 'requests_app/cabinet.html', context)

def submit_request(request):
    """Отправка новой заявки"""
    print("🔵 submit_request вызван")
    
    if request.method == 'POST':
        if 'user_login' not in request.session:
            return JsonResponse({'status': 'error', 'message': 'Не авторизован'}, status=401)
        
        user_login = request.session.get('user_login')
        
        try:
            user = RegisterUser.objects.using('users_db').get(login=user_login)
            
            """Создаем заявку"""
            service_request = ServiceRequest.objects.create(
                full_name=user.full_name,
                organization=request.POST.get('organization'),
                department=request.POST.get('department'),
                payment_doc=request.POST.get('payment_doc', ''),
                request_text=request.POST.get('request_text'),
                status='pending'
            )
            
            print(f"✅ Заявка #{service_request.id} создана")
            
            """Отправляем уведомления в фоновом потоке"""
            def send_emails_thread():
                try:
                    """Клиенту"""
                    send_client_notification(
                        client_email=user.email,
                        client_name=user.full_name,
                        request_id=service_request.id,
                        status='pending'
                    )
                    
                    """Сотрудникам"""
                    from .models import AccessKey
                    employees = AccessKey.objects.using('access_db').filter(
                        department=service_request.department,
                        is_active=True
                    )
                    
                    for emp in employees:
                        send_employee_notification(
                            employee_email=emp.email,
                            employee_name=emp.employee_name,
                            department=service_request.department,
                            request_data={
                                'id': service_request.id,
                                'full_name': service_request.full_name,
                                'organization': service_request.organization,
                                'request_text': service_request.request_text
                            }
                        )
                except Exception as e:
                    print(f"⚠️ Ошибка фоновой отправки email: {e}")
            
            """Запускаем поток"""
            thread = threading.Thread(target=send_emails_thread)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'status': 'success', 'message': 'Заявка успешно отправлена!'})
            
        except RegisterUser.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Пользователь не найден'}, status=404)
        except Exception as e:
            print(f"❌ Ошибка при создании заявки: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

@csrf_exempt
def notify_client_from_app(request):
    """API для отправки уведомлений клиенту из приложения"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print(f"📧 Получен запрос на уведомление: {data}")
            
            request_id = data.get('request_id')
            status = data.get('status')
            comment = data.get('comment', '')
            
            service_request = ServiceRequest.objects.get(id=request_id)
            print(f"📋 Заявка #{request_id} найдена")
            
            """Ищем пользователя по ФИО"""
            user = RegisterUser.objects.using('users_db').filter(full_name=service_request.full_name).first()
            
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
                return JsonResponse({'status': 'success', 'sent': result})
            else:
                print(f"❌ Email не найден для {service_request.full_name}")
                return JsonResponse({'status': 'error', 'message': 'Email не найден'})
                
        except ServiceRequest.DoesNotExist:
            print(f"❌ Заявка {request_id} не найдена")
            return JsonResponse({'status': 'error', 'message': 'Заявка не найдена'}, status=404)
        except Exception as e:
            print(f"❌ Ошибка: {e}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)

"""API для приложения сотрудников"""
@csrf_exempt
def employee_login(request):
    """Вход сотрудника в приложение"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
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
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)


@csrf_exempt
def get_employee_requests(request):
    """Получение заявок для сотрудника (по его отделу)"""
    if request.method == 'GET':
        try:
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
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)}, status=500)
    
    return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)