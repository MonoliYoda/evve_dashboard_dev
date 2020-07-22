from esi.clients import EsiClientProvider
from esi.models import Token
from eve_dashboard import settings
from dashboard.models import LocationName, CharacterName, ContractShipName
from dashboard.models import StructureTimer, PlanetName
from datetime import datetime, timedelta
import pytz
import logging
import time
import json

esi = EsiClientProvider()

with open('invTypes.json', 'r') as jsonfile:
    inv_types = json.load(jsonfile)
with open('shipTypes.json', 'r') as jsonfile:
    ship_types = json.load(jsonfile)


def setup_logger(logger_name, log_file, level=logging.INFO):
    log_setup = logging.getLogger(logger_name)
    formatter = logging.Formatter('%(levelname)s: %(asctime)s %(message)s',
                                  datefmt='%d/%m/%Y %H:%M:%S')
    fileHandler = logging.FileHandler(log_file, mode='a')
    fileHandler.setFormatter(formatter)
    streamHandler = logging.StreamHandler()
    streamHandler.setFormatter(formatter)
    log_setup.setLevel(level)
    log_setup.addHandler(fileHandler)
    log_setup.addHandler(streamHandler)


def logger(msg, level, logfile):
    if logfile == 'stats':
        log = logging.getLogger('log_stats')
    if logfile == 'error':
        log = logging.getLogger('log_error')
    if level == 'info':
        log.info(msg)
    if level == 'warning':
        log.warning(msg)
    if level == 'error':
        log.error(msg)


setup_logger('log_error', settings.LOG_FILE_ERROR)
setup_logger('log_stats', settings.LOG_FILE_STATS)

logger('Logging stats...', 'info', 'stats')
logger('Logging errors...', 'info', 'error')


def prepare_view(request, tokens):
    requested_id = None
    try:
        requested_id = int(request.GET.get('user_id'))
    except Exception as e:
        print('Arg failed')
        print(e)
    # if the user is authed, get the wallet content !
    active_token = find_token(tokens, requested_id)
    char_name = active_token.character_name
    char_id = active_token.character_id
    return active_token, char_name, char_id


def get_user_planets(user_token):
    """Retrieves data on a character's planets.

    Fetches a list of the character's planets from ESI. Attempts to find
    any extractors on each planet, and calculate the cycle completion
    percentage. Gets the planet type and appends to 'name'. Determines if the
    planet requires attention and writes either 'good' or 'bad' into 'health'.

    Args:
        user_id: Int containing the character ID.

    Returns:
        A list of dicts containing planets and their details.
    """
    planets = []
    planet_list = esi.client.Planetary_Interaction.get_characters_character_id_planets(
        character_id=user_token.character_id,
        token=user_token.valid_access_token()
    ).results()
    for planet in planet_list:
        db_planet = PlanetName.objects.filter(
            planet_id=planet['planet_id']
        ).first()
        if db_planet is None:
            planet['name'] = esi.client.Universe.get_universe_planets_planet_id(
                planet_id=planet['planet_id']
            ).results()['name']
            PlanetName(
                planet_id=planet['planet_id'],
                planet_name=planet['name']
            ).save()
        else:
            planet['name'] = db_planet.planet_name
        res = esi.client.Planetary_Interaction.get_characters_character_id_planets_planet_id(
            character_id=user_token.character_id,
            planet_id=planet['planet_id'],
            token=user_token.valid_access_token()
        ).results()
        planet['health'] = 'good'
        planet['extractors'] = []
        planet['last_update'] = planet['last_update'].strftime('%Y-%m-%d %H:%M')
        planet['planet_type'] = planet['planet_type'].capitalize()
        for pin in res['pins']:
            if 'extractor_details' in pin.keys():
                if pin['install_time'] is None:
                    continue
                if pin['expiry_time'] is None:
                    continue
                estart = pin['install_time'].timestamp()
                eend = pin['expiry_time'].timestamp()
                enow = datetime.timestamp(datetime.utcnow())
                epct = int((enow - estart) / (eend - estart) * 100)
                if epct > 100:
                    planet['health'] = 'bad'
                    epct = 100
                install_time = pin['install_time'].strftime('%Y-%m-%d %H:%M')
                expiry_time = pin['expiry_time'].strftime('%Y-%m-%d %H:%M')

                # print('Exctractor percent: {}'.format(epct))
                planet['extractors'].append({
                    'install_time': install_time,
                    'expiry_time': expiry_time,
                    'completion': epct
                })
        if len(planet['extractors']) == 0:
            planet['health'] = 'bad'
        planets.append(planet)
    return planets


def get_contracts(user_token, type):
    """Fetches a list of available Corp Contracts.

    Fetches a list of corp contracts available, if the user has rights to see
    them. Processes and rearranges the data to prepare for displaying in a
    table. Will count duplicate contracts with the same name and price. Will
    attempt to resolve issuer character_id.

    Args:
        corp_id: The corporation id to fetch data for.

    Returns:
        A list of dicts containing the available contracts and their details.
    """
    avail_contracts = []
    corp_id = None
    if type == 'corp':
        corp_id = esi.client.Character.get_characters_character_id(
            character_id=user_token.character_id
        ).result()['corporation_id']
        contracts = esi.client.Contracts.get_corporations_corporation_id_contracts(
            corporation_id=corp_id,
            token=user_token.valid_access_token()
        ).results()
        contracts[:] = [d for d in contracts if d.get('status') == 'outstanding']
    if type == 'character':
        contracts = esi.client.Contracts.get_characters_character_id_contracts(
            character_id=user_token.character_id,
            token=user_token.valid_access_token()
        ).results()
        contracts[:] = [d for d in contracts if d.get(
            'status') == 'outstanding' or d.get('status') == 'finished']
        contracts[:] = [d for d in contracts if d.get('price') != 0]
        contracts[:] = [d for d in contracts if d.get('issuer_id') == user_token.character_id]
    for contract in contracts:
        if type == 'character':
            if contract['date_expired'] < (datetime.utcnow().replace(tzinfo=pytz.UTC) - timedelta(days=7)):
                continue
        contract['bids'] = '-'
        if contract['type'] == 'item_exchange':
            contract['type'] = 'Item exchange'
        if contract['type'] == 'auction':
            bids = []
            if type == 'corp':
                bids = esi.client.Contracts.get_corporations_corporation_id_contracts_contract_id_bids(
                    corporation_id=corp_id,
                    contract_id=contract['contract_id'],
                    token=user_token.valid_access_token()
                ).results()
            elif type == 'character':
                bids = esi.client.Contracts.get_characters_character_id_contracts_contract_id_bids(
                    character_id=user_token.character_id,
                    contract_id=contract['contract_id'],
                    token=user_token.valid_access_token()
                ).results()
            if bids != []:
                contract['price'] = bids[0]['amount']
                contract['bids'] = len(bids)
            contract['type'] = 'Auction'
        # Check if contract is in cache DB
        db_cont = ContractShipName.objects.filter(
            contract_id=contract['contract_id']).first()
        ship_name = ''
        if db_cont is not None:
            ship_name = db_cont.ship_name
        else:
            if type == 'corp':
                items = esi.client.Contracts.get_corporations_corporation_id_contracts_contract_id_items(
                    corporation_id=corp_id,
                    contract_id=contract['contract_id'],
                    token=user_token.valid_access_token()
                ).results()
            elif type == 'character':
                items = esi.client.Contracts.get_characters_character_id_contracts_contract_id_items(
                    character_id=user_token.character_id,
                    contract_id=contract['contract_id'],
                    token=user_token.valid_access_token()
                ).results()
            if len(items) != 0:
                for item in items:
                    if (item['is_included'] and
                            item['quantity'] == 1 and
                            str(item['type_id']) in ship_types):
                        # Probably a ship?
                        ship_name = ship_types[str(item['type_id'])]['typeName']
                        ContractShipName(
                            contract_id=contract['contract_id'],
                            ship_name=ship_name
                        ).save()
                        break
                else:
                    ContractShipName(
                        contract_id=contract['contract_id'],
                        ship_name=''
                    ).save()
        if ship_name != '':
            contract['title'] = '[' + ship_name + '] ' + contract['title']
        count = 0
        for c in avail_contracts:
            if (c['title'] == contract['title'] and
                    c['price'] == '{:,.2f}'.format(contract['price'])):
                count += 1
        # If contract does not already exist, append to avail_contracts
        if count == 0:
            new_contract = {
                'contract_id': contract['contract_id'],  # Contract ID
                'price': '{:,.2f}'.format(contract['price']),  # Price
                'title': contract['title'],  # Description
                'type': contract['type'],  # Auction or exchange
                'status': contract['status'],  # Issuer name
                'count': 1,  # How many duplicates?
                'bids': contract['bids']  # How many bids, if any?
            }
            if type == 'corp':
                character = CharacterName.objects.filter(
                    character_id=contract['issuer_id']).first()
                if character is not None:
                    issuer = character.character_name
                else:
                    issuer = esi.client.Character.get_characters_character_id(
                        character_id=contract['issuer_id']
                    ).result()['name']
                    CharacterName(
                        character_id=contract['issuer_id'],
                        character_name=issuer
                    ).save()
                new_contract['issuer'] = issuer
            avail_contracts.append(new_contract)
        else:
            for item in avail_contracts:
                if item['title'] == contract['title']:
                    item['count'] += 1
                    if (isinstance(item['bids'], int) and
                            isinstance(contract['bids'], int)):
                        item['bids'] += contract['bids']
                    break
    return avail_contracts


def resolve_loc_names(order_list, user_token):
    """Attempts to resolve names for locations of market orders.

    Args:
        order_list: A list of dicts with market orders, as received from ESI.

    Returns:
        A list of dicts containing market orders, with resolved locations into
            'location_name'.e
    """
    if len(order_list) != 0:
        if not isinstance(order_list, list):
            print('Error while resolving loc names: {}'.format(order_list))
            logger('Error while resolving loc names.', 'warning', 'error')
            return order_list
        for order in order_list:
            order['name'] = get_name_by_id(order['type_id'])
            order['price'] = '{:,.2f} ISK'.format(order['price'])
            # Check if location_id exists in cache
            location = LocationName.objects.filter(
                location_id=order['location_id']).first()
            if location is not None:
                order['location_name'] = location.location_name
            # if order['location_id'] in loc_cache.keys():
            #    order['location_name'] = loc_cache[order['location_id']]
            else:  # If not, then we have to try to find it.
                if order['location_id'] < 1000000000:
                    try:
                        station = esi.client.Universe.get_universe_stations_station_id(
                            station_id=order['location_id']
                        ).result()
                        order['location_name'] = station['name']
                        LocationName(
                            location_id=order['location_id'],
                            location_name=station['name']
                        ).save()
                    except Exception as e:
                        order['location_name'] = 'Unknown'
                        print('Error {} at fetching station name.'.format(e))
                        logger('Error {} fetching station name.'.format(e),
                               'error', 'error')
                        logger('User: {}, station ID: {}'
                               .format(user_token.character_name,
                                       order['location_id']), 'error', 'error')
                else:
                    try:
                        structure = esi.client.Universe.get_universe_structures_structure_id(
                            structure_id=order['location_id'],
                            token=user_token.valid_access_token()
                        ).result()
                        order['location_name'] = structure['name']
                        LocationName(
                            location_id=order['location_id'],
                            location_name=station['name']
                        ).save()
                    except Exception as e:
                        order['location_name'] = 'Unknown'
                        print('Error {} at fetching structure name.'.format(e))
                        logger('Error {} fetching structure name.'.format(e),
                               'error', 'error')
                        logger('User: {}, structure ID: {}'
                               .format(user_token.character_name,
                                       order['location_id']), 'error', 'error')
    return order_list


def get_notifications(user_token):
    notifications = []
    notifications = esi.client.Character.get_characters_character_id_notifications(
        character_id=user_token.character_id,
        token=user_token.valid_access_token()
    ).results()
    return notifications


def get_mails(user_token):
    unread = 0
    mails = []
    return unread, mails


def get_name_by_id(id):
    """Resolves typeID into item name from inv_types in EVE static DB.

    Useful for retrieving the name of a ship in a contract.

    Args:
        id: Int containing the requested typeID.

    Returns:
        A string with the name of the requested item.
    """
    for i, dic in enumerate(inv_types):
        if dic['typeID'] == id:
            return dic['typeName']


def find_token(tokens, requested_id):
    for token in tokens:
        if requested_id == token.character_id:
            return token
    return tokens[0]
