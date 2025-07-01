# utils/helpers.py
import re
from typing import Optional

def parse_time_to_minutes(time_str: str) -> Optional[int]:
    """Converte uma string de tempo (ex: 2h, 90m, 2:30) para minutos."""
    time_str = time_str.lower().replace(" ", "")
    # Tenta o formato "1h30m"
    match = re.match(r"^(?:(\d+)h)?(?:(\d+)m?)?$", time_str.replace(":", "h"))
    if match and any(match.groups()):
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        return (hours * 60) + minutes
    # Se for apenas um número, assume que são horas (ex: "2" -> 120 min)
    if time_str.isdigit():
        return int(time_str) * 60
    return None