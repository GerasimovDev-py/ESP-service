from django.db import models

"""МОДЕЛЬ КЛИЕНТОВ (Register_Users)"""
class RegisterUser(models.Model):
    first_name = models.CharField('Имя', max_length=100)
    middle_name = models.CharField('Отчество', max_length=100, blank=True)
    last_name = models.CharField('Фамилия', max_length=100)
    full_name = models.CharField('ФИО', max_length=200, blank=True)
    phone = models.CharField('Телефон', max_length=20)
    email = models.EmailField('Email')
    payment_id = models.CharField('ID платежки', max_length=100, blank=True)
    login = models.CharField('Логин', max_length=100, unique=True)
    password = models.CharField('Пароль', max_length=255)
    created_at = models.DateTimeField('Дата регистрации', auto_now_add=True)

    class Meta:
        app_label = 'requests_app'
        db_table = 'register_users'
        managed = False

    def __str__(self):
        return f"{self.last_name} {self.first_name} {self.middle_name}".strip()

"""МОДЕЛЬ ЗАЯВОК"""
class ServiceRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает рассмотрения'),
        ('in_progress', 'Принята в работу'),
        ('completed', 'Завершена'),
        ('redirected', 'Перенаправлена'),
    ]
    
    DEPARTMENT_CHOICES = [
        ('legal', 'Юридический'),
        ('technical', 'Технический'),
        ('accounting', 'Делопроизводство'),
    ]
    
    user = models.ForeignKey(RegisterUser, on_delete=models.CASCADE, null=True, blank=True, verbose_name='Пользователь')
    full_name = models.CharField('ФИО', max_length=200)
    organization = models.CharField('Организация', max_length=200)
    department = models.CharField('Отдел', max_length=20, choices=DEPARTMENT_CHOICES)
    payment_doc = models.CharField('№ платежного листа', max_length=100, blank=True)
    request_text = models.TextField('Текст заявки')
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='pending')
    employee_response = models.TextField('Ответ сотрудника', blank=True)
    response_date = models.DateTimeField('Дата ответа', null=True, blank=True)
    assigned_to = models.ForeignKey('Employee', null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Ответственный')
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    completed_at = models.DateTimeField('Дата завершения', null=True, blank=True)
    
    class Meta:
        app_label = 'requests_app'
        db_table = 'service_request'
        managed = False
        ordering = ['-created_at']
    
    def __str__(self):
        status_emoji = {
            'pending': '🟡',
            'in_progress': '🟠',
            'completed': '🟢',
            'redirected': '🔄'
        }
        return f"{status_emoji.get(self.status, '⚪')} {self.full_name} - {self.get_department_display()}"

"""МОДЕЛЬ СОТРУДНИКОВ (notificator_data)"""
class Employee(models.Model):
    DEPARTMENT_CHOICES = [
        ('legal', 'Юридический'),
        ('technical', 'Технический'),
        ('accounting', 'Делопроизводство'),
    ]
    
    username = models.CharField('Логин', max_length=50, unique=True)
    password = models.CharField('Пароль', max_length=255)
    full_name = models.CharField('ФИО', max_length=200)
    department = models.CharField('Отдел', max_length=20, choices=DEPARTMENT_CHOICES)
    email = models.EmailField('Email', unique=True)
    access_key = models.CharField('Ключ доступа', max_length=50, unique=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    class Meta:
        app_label = 'requests_app'
        db_table = 'employee'
        managed = False
    
    def __str__(self):
        return f"{self.full_name} ({self.get_department_display()})"

"""МОДЕЛЬ КЛЮЧЕЙ ДОСТУПА (Access_data)"""
class AccessKey(models.Model):
    key_value = models.CharField('Ключ доступа', max_length=50, unique=True)
    department = models.CharField('Отдел', max_length=20)
    employee_name = models.CharField('ФИО сотрудника', max_length=200)
    email = models.EmailField('Email')
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    class Meta:
        app_label = 'requests_app'
        db_table = 'access_keys'
        managed = False
    
    def __str__(self):
        return f"{self.employee_name} - {self.key_value}"