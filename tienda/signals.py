from django.contrib.auth.signals import user_logged_in
from rest_framework.authtoken.models import Token

def create_auth_token(sender, request, user, **kwargs):
    Token.objects.get_or_create(user=user)

user_logged_in.connect(create_auth_token)