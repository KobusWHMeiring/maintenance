from datetime import date, datetime

def extract_dob_from_id(id_number):
    """
    Extracts and formats a date of birth from a South African ID number string.
    Returns a date object or None if the ID is invalid.
    """
    if not isinstance(id_number, str) or len(id_number) != 13 or not id_number.isdigit():
        return None

    try:
        # Extract parts from ID number
        year_prefix = "19" if id_number[0] in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9'] and int(id_number[:2]) > 25 else "20"
        if int(id_number[:2]) < 25: # Crude way to handle century, good enough for now
            year_prefix = "20"
        else:
            year_prefix = "19"
            
        year = int(f"{year_prefix}{id_number[0:2]}")
        month = int(id_number[2:4])
        day = int(id_number[4:6])

        # Validate the date before creating it
        datetime(year=year, month=month, day=day)
        
        return date(year, month, day)
    except (ValueError, TypeError):
        # Handles cases where the date is invalid (e.g., month 13)
        return None

def calculate_age(birthdate):
    """
    Calculates age from a date object.
    Returns age as an integer, or an empty string if birthdate is invalid.
    """
    if not isinstance(birthdate, date):
        return ""
    today = date.today()
    age = today.year - birthdate.year - ((today.month, today.day) < (birthdate.month, birthdate.day))
    return str(age)

def wrap_text(text, limit):
    """
    Wraps a long string of text into two parts at a specified character limit.
    It tries to break at the last space before the limit to avoid splitting words.
    Returns a tuple: (first_line, remaining_text).
    """
    if not text or len(text) <= limit:
        return (text, "")

    # Find the last space within the limit
    break_point = text.rfind(' ', 0, limit)

    if break_point == -1:
        # No space found, so we have to do a hard cut
        break_point = limit

    line1 = text[:break_point].strip()
    line2 = text[break_point:].strip()
    
    return (line1, line2)