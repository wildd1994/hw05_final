import datetime as dt


def year(request):
    """
    Добавляет переменную с текущим годом.
    """
    now = dt.datetime.now()
    return {
        'year': now.year
    }
