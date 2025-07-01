import pytest
from cogs.hr_commands import parse_time_to_minutes

@pytest.mark.parametrize("input_str, expected_minutes", [
    ("2h", 120),
    ("30m", 30),
    ("1h30m", 90),
    ("1:30", 90),
    (" 2h30m ", 150), # Espaços no início/fim, mas não no meio
    ("2", 120),
    ("1h", 60),
    ("0h30m", 30),
])
def test_parse_time_sucesso(input_str, expected_minutes):
    """Verifica se vários formatos de tempo válidos são convertidos corretamente para minutos."""
    assert parse_time_to_minutes(input_str) == expected_minutes

@pytest.mark.parametrize("invalid_input", [
    "abc",
    "1.5h",
    "",
    "h",
    "m",
    "1h 30 m", # Espaços no meio
    "2h 30",   # Formato ambíguo
])
def test_parse_time_formato_invalido(invalid_input):
    """Verifica se formatos inválidos retornam None, como esperado."""
    assert parse_time_to_minutes(invalid_input) is None