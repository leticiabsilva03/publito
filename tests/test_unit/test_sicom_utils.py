# tests/test_unit/test_sicom_utils.py
import pytest
from cogs.sicom_commands import SicomCommands

# Instanciamos o Cog fora dos testes para reutilização.
# Passamos `None` para o bot, pois não precisaremos dele neste teste unitário.
sicom_cog = SicomCommands(bot=None)

@pytest.mark.parametrize("nome_input, resultado_esperado", [
    ("são paulo", "Sao Paulo"),
    ("ABADIA DOS DOURADOS", "Abadia Dos Dourados"),
    ("  cidade com espacos  ", "Cidade Com Espacos"),
])
def test_formatar_nome_valido(nome_input, resultado_esperado):
    """Verifica se nomes válidos são formatados corretamente (sem acentos e em Title Case)."""
    assert sicom_cog._formatar_e_validar_nome(nome_input) == resultado_esperado

@pytest.mark.parametrize("nome_invalido", [
    ("sao paulo 2"),
    ("cidade-com-hifen"),
    ("nome_com_underline"),
    ("cidade@especial"),
])
def test_formatar_nome_invalido_levanta_erro(nome_invalido):
    """Verifica se a função levanta um ValueError para nomes com caracteres inválidos."""
    # 'with pytest.raises' é uma forma elegante de verificar se a sua função
    # se comporta como esperado ao receber um input inválido, levantando o erro correto.
    with pytest.raises(ValueError, match="deve conter apenas letras e espaços"):
        sicom_cog._formatar_e_validar_nome(nome_invalido)