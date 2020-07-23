import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.http.response import HttpResponseBadRequest
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from eve_dashboard import settings
from esi.decorators import token_required, tokens_required
from esi.clients import EsiClientProvider
from esi.models import Token, CallbackRedirect
from dashboard.models import LocationName, CharacterName, ContractShipName
from dashboard.models import StructureTimer, PlanetName
from datetime import datetime, timedelta
from dashboard.utils import get_user_planets, get_contracts, logger, prepare_view, resolve_loc_names, get_name_by_id
import time
import json
import pytz
import string
import random

esi = EsiClientProvider()
logs = logging.getLogger(__name__)

with open('timer_boards_corp.json', 'r') as jsonfile:
    timer_boards_corp = json.load(jsonfile)


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


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def index(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    logger('User {} requested page /index'
           .format(char_name),
           'info', 'stats')
    # Get planet details.
    # TODO: Move this over to AJAX
    user_list = []
    for token in tokens:
        user_list.append({
            'user_id': token.character_id,
            'user_name': token.character_name
        })
    print('User list: {}'.format(user_list))
    planets = get_user_planets(active_token)
    logger('/contracts generated in: {}'.format(time.time() - start_time),
           'info', 'stats')
    context = {
        'name': char_name,
        'char_id': char_id,
        'planets': planets,
        'tokens': user_list,
        'page_link': 'index',
        'page_name': 'Dashboard'
    }
    return render(request, 'dashboard/index.html', context)


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def contracts(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    user_list = []
    for token in tokens:
        user_list.append({
            'user_id': token.character_id,
            'user_name': token.character_name
        })
    logger('User {} requested page /contracts'
           .format(char_name),
           'info', 'stats')
    # avail_contracts = get_corp_contracts(corporation_id)
    # print(wallet.data)
    logger('/contracts generated in: {}'.format(time.time() - start_time),
           'info', 'stats')
    context = {
        'atoken': active_token.valid_access_token(),
        'name': char_name,
        'char_id': char_id,
        'tokens': user_list,
        'page_link': 'contracts',
        'page_name': 'Contracts'
    }
    return render(request, 'dashboard/contracts.html', context)


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def market(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    user_list = []
    for token in tokens:
        user_list.append({
            'user_id': token.character_id,
            'user_name': token.character_name
        })
    logger('User {} requested page /market'
           .format(char_name),
           'info', 'stats')
    logger('/market generated in: {}'.format(time.time() - start_time),
           'info', 'stats')
    context = {
        'name': char_name,
        'char_id': char_id,
        'tokens': user_list,
        'page_link': 'market',
        'page_name': 'Market'
    }
    return render(request, 'dashboard/market.html', context)


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def calendar(request, tokens):
    start_time = time.time()
    char_name = None
    event_list = None
    output_list = None
    # if the user is authed, get the wallet content !
    active_token, char_name, char_id = prepare_view(request, tokens)
    user_list = []
    for token in tokens:
        user_list.append({
            'user_id': token.character_id,
            'user_name': token.character_name
        })
    logger('User {} requested page /calendar'
           .format(char_name),
           'info', 'stats')
    output_list = []
    event_list = esi.client.Calendar.get_characters_character_id_calendar(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).result()
    for event in event_list:
        print('——')
        print(event)
        res = esi.client.Calendar.get_characters_character_id_calendar_event_id(
            character_id=char_id,
            event_id=event['event_id'],
            token=active_token.valid_access_token()
        ).result()
        event_start = res['date']
        event_end = event_start + timedelta(minutes=res['duration'])
        if res['importance'] == 0:
            color = '#0073b7'
        else:
            color = '#f56954'
        output_list.append({
            'title': res['title'],
            'start': time.mktime(event_start.timetuple()),
            'end': time.mktime(event_end.timetuple()),
            'backgroundColor': color,
            'borderColor': color
        })
    logger('/calendar generated in: {}'.format(time.time() - start_time),
           'info', 'stats')
    context = {
        'name': char_name,
        'char_id': char_id,
        'event_list': output_list,
        'tokens': user_list,
        'page_link': 'calendar',
        'page_name': 'Calendar'
    }
    return render(request, 'dashboard/calendar.html', context)

# ————————————————————————
# AJAX Things
# ————————————————————————


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_timers(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    corporation_id = esi.client.Character.get_characters_character_id(
        character_id=char_id
    ).result()['corporation_id']
    try:
        with open('timer_boards_corp.json', 'r') as jsonfile:
            timer_boards_corp = json.load(jsonfile)
    except Exception as e:
        print('Error reading timers from file: {}'.format(e))
    timers_list = []
    if str(corporation_id) in timer_boards_corp.keys():
        for timer in timer_boards_corp[str(corporation_id)]:
            timers_list.append([timer['location'], timer['name'],
                                timer['timer_type'],
                                timer['type'], timer['time'] + 'Z',
                                timer['notes'], timer['name']])
    return JsonResponse({'data': timers_list})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_new_timer(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    logger('User {} added a new timer.'
           .format(char_name),
           'info', 'stats')
    print('Data: {}'.format(json.loads(request.data)))
    data = json.loads(request.data)
    logger(str(data), 'info', 'stats')
    # return JsonResponse({'status': 'debug return'})
    try:
        namesplit = data['inputDscan'].split('\t')
        loc, name = namesplit[1].split(' - ', 1)
        type = namesplit[2]
        type_id = namesplit[0]
    except Exception as e:
        logger('Failed parsing Dscan: {}'.format(data), 'error', 'error')
        logger(str(e), 'error', 'error')
        return JsonResponse({'status': 'error: Dscan'})
    try:
        data['timer_type']
    except Exception as e:
        logger('Failed parsing Timer type: {}'.format(data),
               'error', 'error')
        logger(str(e), 'error', 'error')
        return JsonResponse({'status': 'error: timer_type'})
    days = '0'
    try:
        if 'd' in data['inputTimeleft']:
            days, time = data['inputTimeleft'].split('d', 1)
        elif 'D' in data['inputTimeleft']:
            days, time = data['inputTimeleft'].split('D', 1)
        else:
            time = data['inputTimeleft']
    except Exception as e:
        logger('Failed parsing Time left: {}'.format(data),
               'error', 'error')
        logger(str(e), 'error', 'error')
        return JsonResponse({'status': 'error: inputTimeleft'})
    try:
        timer_notes = data['inputNotes']
    except Exception as e:
        logger('Failed parsing Timer notes: {}'.format(data),
               'error', 'error')
        logger(str(e), 'error', 'error')
        return JsonResponse({'status': 'error: timer_notes'})
    # print(timeparse(time))
    time_left = timedelta(days=int(days), seconds=timeparse(time))
    # return JsonResponse({'status': 'debug return'})
    corporation_id = esi.client.Character.get_characters_character_id(
        character_id=char_id
    ).result()['corporation_id']
    StructureTimer(
        tid=random.randint(10000000, 99999999),
        timer_corp=corporation_id,
        location=loc,
        timer_type=data['timer_type'],
        structure_type_id=type_id,
        structure_type_name=type,
        structure_name=name,
        structure_corp=0,
        time=(datetime.utcnow() + time_left).isoformat(),
        notes=timer_notes
    ).save()
    return JsonResponse({'status': 'success'})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_remove_timer(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    logger('User {} is removing a timer.'
           .format(char_name),
           'info', 'stats')
    data = json.loads(request.data)
    logger(str(data), 'info', 'stats')
    corporation_id = esi.client.Character.get_characters_character_id(
        character_id=char_id
    ).result()['corporation_id']
    if str(corporation_id) in timer_boards_corp.keys():
        corp_contracts = timer_boards_corp[str(corporation_id)]
        for i in range(len(corp_contracts)):
            try:
                if data['sName'] == corp_contracts[i]['name']:
                    del corp_contracts[i]
                    timer_boards_corp[str(corporation_id)] = corp_contracts
                    with open('timer_boards_corp.json', 'w') as jsonfile:
                        json.dump(timer_boards_corp, jsonfile,
                                  ensure_ascii=False, indent=4)
                    return JsonResponse({'status': 'success'})
            except Exception as e:
                logger('Failed parsing Structure name: {}'.format(data),
                       'error', 'error')
                logger(str(e), 'error', 'error')
                return JsonResponse({'status': 'error: sName'})
    else:
        return JsonResponse({'status': 'not found'})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_corp_contracts(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    acc_token = active_token.valid_access_token()
    avail_contracts = get_contracts(active_token, 'corp')
    for contract in avail_contracts:
        contract['contract_id'] = [contract['contract_id'], acc_token]
    return JsonResponse({"data": avail_contracts})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_planets(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    planets = get_user_planets(active_token)
    return JsonResponse({planets})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_user_contracts(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    acc_token = active_token.valid_access_token()
    avail_contracts = get_contracts(active_token, 'character')
    for contract in avail_contracts:
        contract['contract_id'] = [contract['contract_id'], acc_token]
    return JsonResponse({"data": avail_contracts})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_walletbalance(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    result = esi.client.Wallet.get_characters_character_id_wallet(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).result()
    try:
        return HttpResponse('{:,.2f}'.format(result))
    except Exception as e:
        logger('Error getting wallet balance:', 'error', 'error')
        logger('Error: {}, response: {}'.format(str(e), result),
               'error', 'error')
        print('Error getting wallet balance: {}'.format(e))
        return HttpResponse('0')


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_activeorders(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    result = esi.client.Market.get_characters_character_id_orders(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).result()
    order_count = len(result)
    return HttpResponse(str(order_count))


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_24htransactions(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    transactions_24h = 0
    journal = esi.client.Wallet.get_characters_character_id_wallet_journal(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).result()
    journal.reverse()
    # Convert journal list
    for entry in journal:
        if entry['date'] >= (datetime.utcnow().replace(tzinfo=pytz.UTC) -
                             timedelta(days=1)):
            transactions_24h += 1
    return HttpResponse(str(transactions_24h))


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_walletjournal(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    journal = esi.client.Wallet.get_characters_character_id_wallet_journal(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).result()
    journal.reverse()
    balance_list = []
    date_list = []
    # Convert journal list
    for entry in journal:
        timestamp = entry['date'].strftime("%m-%d")
        if timestamp in date_list:
            continue
        date_list.append(timestamp)
        balance_list.append(round(entry['balance'] / 1000000, 2))
    return JsonResponse({'labels': date_list, 'data': balance_list})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def cal_even_count(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    events = esi.client.Calendar.get_characters_character_id_calendar(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).result()
    return HttpResponse(str(len(events)))


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def contract_count(request, tokens):
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    corporation_id = esi.client.Character.get_characters_character_id(
        character_id=char_id
    ).result()['corporation_id']
    contracts = esi.client.Contracts.get_corporations_corporation_id_contracts(
        corporation_id=corporation_id,
        token=active_token.valid_access_token()
    ).result()
    avail_contracts = 0
    # Loop through pulled contracts
    for contract in contracts:
        # Compute only if contract is active
        if contract['status'] == 'outstanding':
            avail_contracts += 1
    return HttpResponse(str(avail_contracts))


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def get_market_active(request, tokens):
    active_orders = []
    active_orders_output = []
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    active_orders = esi.client.Market.get_characters_character_id_orders(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).result()
    active_orders = resolve_loc_names(active_orders, active_token)
    for order in active_orders:
        order['name'] = get_name_by_id(order['type_id'])
        issued = order['issued'].strftime('%Y-%m-%d %H:%M')
        order['issued'] = "".join(issued)
        if 'is_buy_order' not in order.keys():
            order['is_buy_order'] = False
        active_orders_output.append({
            'name': order['name'],
            'issued': order['issued'],
            'price': order['price'],
            'location_name': order['location_name'],
            'duration': order['duration'],
            'is_buy_order': order['is_buy_order'],
            'volume_total': order['volume_total'],
            'volume_remain': order['volume_remain']
        })
    return JsonResponse({"data": active_orders_output})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def get_market_history(request, tokens):
    order_history = []
    order_history_output = []
    start_time = time.time()
    active_token, char_name, char_id = prepare_view(request, tokens)
    order_history = esi.client.Market.get_characters_character_id_orders_history(
        character_id=char_id,
        token=active_token.valid_access_token()
    ).results()
    order_history = resolve_loc_names(order_history, active_token)
    for order in order_history:
        if order['duration'] == 0:
            continue
        order['name'] = get_name_by_id(order['type_id'])
        issued = order['issued'].strftime('%Y-%m-%d %H:%M')
        order['issued'] = "".join(issued)
        if 'is_buy_order' not in order.keys():
            order['is_buy_order'] = False
        order_history_output.append({
            'name': order['name'],
            'issued': order['issued'],
            'price': order['price'],
            'location_name': order['location_name'],
            'duration': order['duration'],
            'is_buy_order': order['is_buy_order'],
            'volume_total': order['volume_total'],
            'volume_remain': order['volume_remain']
        })
    return JsonResponse({"data": order_history_output})
