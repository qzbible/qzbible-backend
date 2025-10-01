import re

def clean_string(s):
    if isinstance(s, str):
        return re.sub(r'^"+|"+$', '', s)  # Supprime les guillemets au début et à la fin
    return s
