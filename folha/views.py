from datetime import datetime, timedelta

from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login as auth_login
from django.contrib.auth.forms import UserCreationForm
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils import timezone

from .supabase_client import supabase


def _chave_rate_limit(email):
    return f"login_rate_limit:{(email or '').strip().lower()}"


def _usuario_por_email(email):
    if not email:
        return None
    return get_user_model().objects.filter(email__iexact=email).first()


def _login_local(email, senha):
    usuario = _usuario_por_email(email)
    if usuario and usuario.check_password(senha):
        return usuario
    return None


def fazer_login(request):
    if 'access_token' in request.session or request.user.is_authenticated:
        return redirect('dashboard')

    if request.method == 'POST':
        email = (request.POST.get('email') or '').strip().lower()
        senha = request.POST.get('senha') or ''

        if not email or not senha:
            messages.error(request, "Informe e-mail e senha.")
            return redirect('login')

        lock_until = request.session.get('login_lock_until')
        if lock_until:
            lock_until_dt = datetime.fromisoformat(lock_until)
            if timezone.now() < lock_until_dt:
                restante = int((lock_until_dt - timezone.now()).total_seconds())
                minutos = restante // 60
                segundos = restante % 60
                messages.error(request, f"Muitas tentativas inválidas. Tente novamente em {minutos} min e {segundos} s.")
                return redirect('login')

            request.session.pop('login_lock_until', None)
            request.session.pop('login_attempts', None)
            request.session.pop('login_lock_duration', None)

        try:
            resposta = supabase.auth.sign_in_with_password({
                "email": email,
                "password": senha,
            })

            cache.delete(_chave_rate_limit(email))
            request.session.pop('login_attempts', None)
            request.session.pop('login_lock_until', None)
            request.session.pop('login_lock_duration', None)
            request.session['access_token'] = resposta.session.access_token
            request.session['user_id'] = resposta.user.id
            request.session['user_email'] = resposta.user.email

            messages.success(request, f"Bem-vindo, {resposta.user.email}!")
            return redirect('dashboard')

        except Exception:
            usuario = _login_local(email, senha)
            if usuario is not None:
                cache.delete(_chave_rate_limit(email))
                request.session.pop('login_attempts', None)
                request.session.pop('login_lock_until', None)
                request.session.pop('login_lock_duration', None)
                auth_login(request, usuario)
                request.session['access_token'] = 'django-auth'
                request.session['user_id'] = usuario.pk
                request.session['user_email'] = usuario.email or usuario.username
                messages.success(request, f"Bem-vindo, {usuario.email or usuario.username}!")
                return redirect('dashboard')

            tentativas = int(request.session.get('login_attempts', 0)) + 1
            request.session['login_attempts'] = tentativas

            if tentativas >= 3:
                duracao = int(request.session.get('login_lock_duration', 30 * 60))
                nova_duracao = max(30 * 60, duracao * 2)
                request.session['login_lock_duration'] = nova_duracao
                request.session['login_lock_until'] = (timezone.now() + timedelta(seconds=nova_duracao)).isoformat()
                messages.error(request, f"Muitas tentativas inválidas. Conta bloqueada por {nova_duracao // 60} minutos.")
                return redirect('login')

            cache.set(_chave_rate_limit(email), tentativas, timeout=3600)
            messages.error(request, "E-mail ou senha inválidos.")
            return redirect('login')

    return render(request, 'login.html')


def cadastro(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            usuario = form.save()
            auth_login(request, usuario)
            request.session['access_token'] = 'django-auth'
            request.session['user_id'] = usuario.pk
            request.session['user_email'] = usuario.email or usuario.username
            messages.success(request, "Usuário cadastrado com sucesso!")
            return redirect('dashboard')
    else:
        form = UserCreationForm()

    return render(request, 'cadastro.html', {'form': form})


def fazer_logout(request):
    request.session.flush()
    messages.info(request, "Você saiu do sistema.")
    return redirect('login')


def dashboard(request):
    if 'access_token' not in request.session and not request.user.is_authenticated:
        messages.warning(request, "Faça login para continuar.")
        return redirect('login')

    if request.user.is_authenticated:
        email_usuario = request.user.email or request.user.username
    else:
        email_usuario = request.session.get('user_email')

    contexto = {'email_usuario': email_usuario}
    return render(request, 'dashboard.html', contexto)
