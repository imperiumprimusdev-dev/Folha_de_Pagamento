from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CadastroUsuarioTests(TestCase):
    def test_cadastro_exibe_formulario(self):
        response = self.client.get(reverse('cadastro'))
        self.assertEqual(response.status_code, 200)

    def test_cadastro_cria_usuario_no_banco(self):
        response = self.client.post(
            reverse('cadastro'),
            {
                'username': 'novo_usuario',
                'email': 'novo@email.com',
                'password1': 'SenhaForte123!',
                'password2': 'SenhaForte123!',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue(get_user_model().objects.filter(username='novo_usuario').exists())


class LoginRateLimitTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='usuario_teste',
            email='usuario@email.com',
            password='SenhaForte123!'
        )

    def test_login_por_email_aceita_usuario_local(self):
        response = self.client.post(
            reverse('login'),
            {'email': 'usuario@email.com', 'senha': 'SenhaForte123!'}
        )

        self.assertEqual(response.status_code, 302)
        self.assertTrue('_auth_user_id' in self.client.session)

    def test_login_trava_apos_tres_tentativas_invalidas(self):
        for _ in range(3):
            self.client.post(
                reverse('login'),
                {'email': 'usuario@email.com', 'senha': 'senha-errada'}
            )

        response = self.client.post(
            reverse('login'),
            {'email': 'usuario@email.com', 'senha': 'SenhaForte123!'}
        )

        self.assertEqual(response.status_code, 302)
        self.assertIn('login_lock_until', self.client.session)
