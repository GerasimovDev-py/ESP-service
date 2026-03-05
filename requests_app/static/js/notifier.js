document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('requestForm');
    const messageDiv = document.getElementById('message');
    const requestsList = document.getElementById('requestsList');
    const requestsCount = document.getElementById('requestsCount');
    
    const successModal = new bootstrap.Modal(document.getElementById('successModal'));
    
    if (form) {
        form.addEventListener('submit', async function(e) {
            e.preventDefault();
            
            if (!form.checkValidity()) {
                e.stopPropagation();
                form.classList.add('was-validated');
                return;
            }
            
            const formData = new FormData(form);
            const submitButton = form.querySelector('button[type="submit"]');
            const originalText = submitButton.innerHTML;
            
            submitButton.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Отправка...';
            submitButton.disabled = true;
            
            try {
                const response = await fetch('/submit/', {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-CSRFToken': formData.get('csrfmiddlewaretoken')
                    }
                });
                
                const data = await response.json();
                
                if (data.status === 'success') {
                    document.getElementById('modalMessage').textContent = data.message;
                    successModal.show();
                    
                    form.reset();
                    form.classList.remove('was-validated');
                    
                    loadRequests();
                    
                    const listTab = document.getElementById('list-tab');
                    if (listTab) {
                        bootstrap.Tab.getOrCreateInstance(listTab).show();
                    }
                } else {
                    showMessage('danger', 'Ошибка при отправке заявки');
                }
            } catch (error) {
                console.error('Error:', error);
                showMessage('danger', 'Ошибка соединения с сервером');
            } finally {
                submitButton.innerHTML = originalText;
                submitButton.disabled = false;
            }
        });
    }
    
    function showMessage(type, text) {
        messageDiv.innerHTML = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${type === 'success' ? 'check-circle' : 'exclamation-triangle'} me-2"></i>
                ${text}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        setTimeout(() => {
            const alert = messageDiv.querySelector('.alert');
            if (alert) {
                alert.classList.remove('show');
                setTimeout(() => {
                    messageDiv.innerHTML = '';
                }, 150);
            }
        }, 5000);
    }

    async function loadRequests() {
        if (!requestsList) return;
        
        try {
            const response = await fetch('/api/new-requests/');
            const data = await response.json();
            
            if (data.requests.length === 0) {
                requestsList.innerHTML = `
                    <div class="text-center text-muted py-5">
                        <i class="bi bi-inbox fs-1 d-block mb-3"></i>
                        <p>Нет новых заявок</p>
                    </div>
                `;
                if (requestsCount) requestsCount.textContent = '0';
                return;
            }
            
            let html = '';
            data.requests.forEach((req, index) => {
                const date = new Date(req.created_at);
                const formattedDate = date.toLocaleString('ru-RU', {
                    day: '2-digit',
                    month: '2-digit',
                    year: 'numeric',
                    hour: '2-digit',
                    minute: '2-digit'
                });
                
                html += `
                    <div class="request-item ${index < 3 ? 'new' : ''}" style="animation-delay: ${index * 0.1}s">
                        <div class="request-header">
                            <span class="request-department">
                                <i class="bi bi-tag me-1"></i>${req.department}
                            </span>
                            <span class="request-date">
                                <i class="bi bi-clock"></i>
                                ${formattedDate}
                            </span>
                        </div>
                        <div class="request-author">
                            <i class="bi bi-person-circle me-2 text-primary"></i>
                            ${req.full_name}
                        </div>
                        <div class="request-organization">
                            <i class="bi bi-building"></i>
                            ${req.organization}
                        </div>
                        <div class="request-text">
                            <i class="bi bi-chat-quote me-2 text-muted"></i>
                            ${req.request_text}
                        </div>
                    </div>
                `;
            });
            
            requestsList.innerHTML = html;
            if (requestsCount) requestsCount.textContent = data.requests.length;
            
        } catch (error) {
            console.error('Error loading requests:', error);
            requestsList.innerHTML = `
                <div class="text-center text-danger py-5">
                    <i class="bi bi-exclamation-triangle fs-1 d-block mb-3"></i>
                    <p>Ошибка загрузки заявок</p>
                </div>
            `;
        }
    }
    
    loadRequests();
    
    setInterval(loadRequests, 30000);
});