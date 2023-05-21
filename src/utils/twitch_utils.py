from utils.errors import TimeNotFound, TargetNotFound
from utils.db_handler import DB


def target_finder(db: DB, request: str) -> str:
    words = request.split(' ')
    for word in words:
        if word.startswith('@'):
            target = word
            target = target.strip('@')
            target = target.strip('\n')
            target = target.strip('\r')
            target = target.strip(' ')
            db.check_user_exists(target)
            return target
    raise TargetNotFound


def time_finder(request: str) -> dict:
    units = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    for unit in units.keys():
        if unit in request:
            try:
                time = int(request.strip(unit))
            except ValueError:
                raise TimeNotFound
            return {'time': time, 'unit': unit}
    # if no unit is found, default to minutes
    unit = 'm'
    request = request.strip(unit)
    try:
        time = int(request)
    except ValueError:
        raise TimeNotFound
    return {'time': time, 'unit': unit}
