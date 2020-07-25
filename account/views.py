from django.shortcuts import render, redirect, get_object_or_404
from dashboard.utils import logger
from django.contrib.auth.models import User
from django.http.response import HttpResponseBadRequest
from django.contrib.auth import login, logout
from esi.models import Token, CallbackRedirect
from esi.decorators import token_required
from eve_dashboard import settings
import random
import logging
import string

logs = logging.getLogger(__name__)


# Create your views here.
def receive_callback(request):
    """
    Parses SSO callback, validates, retrieves :model:`esi.Token`,
    and internally redirects to the target url.
    """
    logs.debug(
        "Received callback for %s session %s",
        request.user,
        request.session.session_key[:5]
    )
    # make sure request has required parameters
    code = request.GET.get('code', None)
    state = request.GET.get('state', None)
    try:
        assert code
        assert state
    except AssertionError:
        logger.debug("Missing parameters for code exchange.")
        return HttpResponseBadRequest()

    callback = get_object_or_404(
        CallbackRedirect, state=state, session_key=request.session.session_key
    )
    token = Token.objects.create_from_request(request)
    if not request.user.is_authenticated:
        try:
            first_name, last_name = token.character_name.split(' ', 1)
        except ValueError:
            first_name = token.character_name
            last_name = ''
        char_id = token.character_id
        print('Attempting to auth user ID: {}'.format(char_id))
        # user = authenticate(username=char_id, password='')
        user = User.objects.filter(
            username=char_id
        ).first()
        if user is not None:
            print('User {} auth success.'.format(token.character_name))
            login(request, user)
        else:
            print('User {} auth failure. Creating new user.'.format(token.character_name))
            letters = string.ascii_lowercase
            user = User.objects.create_user(
                username=char_id,
                password=''.join(random.choice(letters) for i in range(32)),
                first_name=first_name,
                last_name=last_name
            )
            login(request, user)
            token.user = user
            token.save()
    callback.token = token
    callback.save()
    logs.debug(
        "Processed callback for %s session %s. Redirecting to %s",
        request.user,
        request.session.session_key[:5],
        callback.url
    )
    return redirect(callback.url)


@token_required(scopes=settings.ESI_SSO_SCOPES)
def add_user(request, token):
    return redirect('dashboard-index')


def logout_user(request):
    if request.user.is_authenticated:
        logout(request)
    return redirect('dashboard-index')
