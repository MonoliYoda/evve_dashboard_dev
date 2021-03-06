import logging
from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.core.serializers import serialize
from eve_dashboard import settings
from esi.decorators import tokens_required
from esi.clients import EsiClientProvider
from eveuniverse.models import EveSolarSystem, EveType
from dashboard.models import StructureTimer, Corporation
from datetime import datetime, timedelta
from dashboard.utils import get_user_planets, get_contracts, logger, prepare_view, resolve_loc_name
from pytimeparse.timeparse import timeparse
import json
import time
import pytz
import random

esi = EsiClientProvider()
logs = logging.getLogger(__name__)


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
    active_token, char_name, char_id = prepare_view(request, tokens)
    corporation_id = esi.client.Character.get_characters_character_id(
        character_id=char_id
    ).result()['corporation_id']
    timer_boards_corp = serialize(
        'json', StructureTimer.objects.filter(timer_corp=corporation_id).all())
    timers_list = []
    for timer in json.loads(timer_boards_corp):
        fields = timer['fields']
        timers_list.append([{'location': fields['location'], 'ownerID': fields['structure_corp']},
                            fields['structure_name'],
                            fields['timer_type'],
                            fields['structure_type_name'], fields['time'],
                            fields['notes'], fields['tid']])
    return JsonResponse({'data': timers_list})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_new_timer(request, tokens):
    active_token, char_name, char_id = prepare_view(request, tokens)
    logger('User {} added a new timer.'
           .format(char_name),
           'info', 'stats')
    print('Data: {}'.format(request.body))
    data = json.loads(request.body)
    logger(str(data), 'info', 'stats')
    namesplit = -1
    loc = ''
    str_name = ''
    str_type_name = ''
    str_type_id = 0
    owner_id = 0
    if data['corpOwner'] is not None:
        owner_obj = Corporation.objects.filter(id=int(data['corpOwner'])).first()
        if owner_obj is not None:
            owner_id = owner_obj.id
    else:
        owner_id = 0
    try:
        namesplit = data['inputDscan'].split('\t', 3)
        loc, str_name = namesplit[1].split(' - ', 1)
        str_type_name = namesplit[2]
        str_type_id = namesplit[0]
    except Exception as e:
        logger('Failed parsing Dscan: {}'.format(data), 'error', 'error')
        logger(str(e), 'error', 'error')
        namesplit = data['inputDscan'].split(' ')
        name_words = namesplit.copy()
        print('Words: {}'.format(namesplit))
        for item in namesplit:
            print('Parsing word: {}'.format(item.capitalize()))
            system = EveSolarSystem.objects.filter(name=item.capitalize()).first()
            if system is not None:
                print('System: {}'.format(system))
                loc = system.name
                name_words.remove(item)
            type = EveType.objects.filter(name=item.capitalize()).first()
            if type is not None:
                print('Type: {}'.format(type))
                str_type_name = type.name
                str_type_id = type.id
                name_words.remove(item)
        str_name = ' '.join(name_words)
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
        structure_type_id=str_type_id,
        structure_type_name=str_type_name,
        structure_name=str_name,
        structure_corp=owner_id,
        time=(datetime.utcnow() + time_left).replace(tzinfo=pytz.UTC).isoformat(),
        notes=timer_notes
    ).save()
    return JsonResponse({'status': 'success'})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_remove_timer(request, tokens):
    active_token, char_name, char_id = prepare_view(request, tokens)
    logger('User {} is removing a timer.'
           .format(char_name),
           'info', 'stats')
    data = json.loads(request.body)
    logger(str(data), 'info', 'stats')
    corporation_id = esi.client.Character.get_characters_character_id(
        character_id=char_id
    ).result()['corporation_id']
    timer = StructureTimer.objects.filter(
        timer_corp=corporation_id,
        tid=data['tid']
    ).all()
    if timer is not None:
        timer.delete()
        return JsonResponse({'status': 'success'})
    else:
        return JsonResponse({'status': 'not found'})


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def ajax_get_corp_contracts(request, tokens):
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
    for order in active_orders:
        order['location_name'] = resolve_loc_name(order['location_id'], active_token)
        order_item, _ = EveType.objects.get_or_create_esi(id=order['type_id'])
        order['name'] = order_item.name
        order['price'] = '{:,.2f} ISK'.format(order['price'])
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
    for order in order_history:
        if order['duration'] == 0:
            continue
        order['location_name'] = resolve_loc_name(order['location_id'], active_token)
        order_item, _ = EveType.objects.get_or_create_esi(id=order['type_id'])
        order['name'] = order_item.name
        order['price'] = '{:,.2f} ISK'.format(order['price'])
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


@tokens_required(scopes=settings.ESI_SSO_SCOPES)
def api_search_corp(request, tokens):
    search_string = request.GET.get('search')
    corp_list = []
    corp_id_list = esi.client.Search.get_search(
        categories=['corporation'],
        search=search_string
    ).results()['corporation']
    for corp_id in corp_id_list:
        corp_obj = Corporation.objects.filter(id=corp_id).first()
        if corp_obj is None:
            corp = esi.client.Corporation.get_corporations_corporation_id(
                corporation_id=corp_id
            ).results()
            corp_obj = Corporation(
                id=corp_id,
                name=corp['name'],
                ticker=corp['ticker']
            )
            corp_obj.save()
        corp_list.append({
            'id': corp_obj.id,
            'name': corp_obj.name,
            'ticker': corp_obj.ticker}
        )
    return JsonResponse({'results': corp_list})
