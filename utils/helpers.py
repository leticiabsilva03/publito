# utils/helpers.py
import re
from typing import Optional

def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Converte uma string de tempo (ex: "2h", "2:30", "90m") para minutos."""
    # Limpa e normaliza a string de entrada primeiro
    s = time_str.strip().lower()

    # Tenta o formato HH:MM primeiro, pois é inequívoco
    match_colon = re.fullmatch(r'(\d+):(\d{1,2})', s)
    if match_colon:
        return int(match_colon.group(1)) * 60 + int(match_colon.group(2))

    # Tenta o formato de número simples (considerado horas)
    if s.isdigit():
        return int(s) * 60

    # Tenta o formato com h e/ou m.
    # Esta regex é mais estrita e não permite espaços entre o número e a letra (ex: '1 h' é inválido).
    # Permite um espaço opcional entre a parte das horas e a parte dos minutos (ex: '1h 30m' é válido).
    match_hm = re.fullmatch(r'^(?:(\d+)h)?\s*(?:(\d+)m)?$', s)

    # Verifica se a regex correspondeu à string inteira e se capturou algum grupo.
    if match_hm and any(match_hm.groups()):
        # Verifica se a string original não é apenas "h" ou "m" ou vazia
        if s in ('h', 'm', ''):
            return None

        hours = int(match_hm.group(1) or 0)
        minutes = int(match_hm.group(2) or 0)
        return hours * 60 + minutes
     
    return None # Retorna None para qualquer outro formato inválido.