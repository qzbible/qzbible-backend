from datetime import datetime, timedelta

def get_week_date_range(year: int, week: int):
    """
    Retourne la plage de dates (début, fin) d'une semaine ISO donnée.
    - year : année
    - week : numéro de la semaine ISO (1-53)
    
    Retourne deux chaînes de caractères au format 'YYYY-MM-DD' : (début, fin)
    """
    # Le lundi de la première semaine ISO est le premier jour de la semaine ISO
    first_day_of_year = datetime(year, 1, 4)  # Le 4 janvier est toujours dans la semaine 1
    first_monday = first_day_of_year - timedelta(days=first_day_of_year.isoweekday() - 1)

    start_of_week = first_monday + timedelta(weeks=week - 1)
    end_of_week = start_of_week + timedelta(days=6)

    return start_of_week.strftime("%Y-%m-%d"), end_of_week.strftime("%Y-%m-%d")
