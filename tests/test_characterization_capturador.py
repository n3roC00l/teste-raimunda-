"""
Caracterização de capturador.py.

Este script importa `cv2` e `picamera2` e ABRE A CÂMERA no nível de módulo
(fora de `if __name__ == "__main__":`) — então não dá para importá-lo nem
executá-lo fora do Raspberry Pi com a câmera conectada. Isso é, em si, um
achado de testabilidade: ver docs/MELHORIAS.md frente #7 e o teste
`test_import_no_nivel_de_modulo_e_um_achado_de_testabilidade` abaixo.

O que dá para caracterizar sem hardware: o FORMATO do nome de arquivo e os
parâmetros de captura, pinados a partir do código-fonte (sem executar).
Caracterização de ponta a ponta (captura real) precisa rodar no Pi —
checklist em tests/CHECKLIST-CAMPO.md.

Rodar:  python -m pytest tests/test_characterization_capturador.py -q
"""

from pathlib import Path

CAMINHO = Path(__file__).resolve().parent.parent / "capturador.py"


def _fonte():
    return CAMINHO.read_text(encoding="utf-8")


def test_formato_do_timestamp_no_nome_do_arquivo_pinado():
    assert "%Y-%m-%d_%H-%M-%S-%f" in _fonte(), (
        "o formato do timestamp no nome do arquivo mudou — se foi "
        "intencional, atualize sistema/capturador.py.md no vault e este teste"
    )


def test_padrao_do_nome_do_arquivo_pinado():
    assert 'nome_arquivo = f"{SETOR_ATUAL}_{timestamp_arquivo}.jpg"' in _fonte()


def test_setor_vem_do_arquivo_relido_a_cada_foto():
    # troca de carreira sem parar a câmera: o setor não é mais só o --setor
    # de arranque, é relido de config.ARQUIVO_SETOR dentro do loop.
    fonte = _fonte()
    assert "'--setor'" in fonte
    assert "required=True" not in fonte            # deixou de ser obrigatório
    assert "config.ARQUIVO_SETOR" in fonte
    assert "_setor_atual()" in fonte
    # a releitura acontece dentro do while (antes do capture_file)
    loop = fonte.split("while True:", 1)[1]
    assert "_setor_atual()" in loop


def test_intervalo_e_resolucao_vem_do_config():
    fonte = _fonte()
    assert "config.INTERVALO_CAPTURA_S" in fonte
    assert "config.RESOLUCAO_CAPTURA" in fonte


def test_import_no_nivel_de_modulo_e_um_achado_de_testabilidade():
    """
    NÃO é um teste de comportamento — é um lembrete executável. A inicialização
    da câmera roda fora de `if __name__ == "__main__":`, então este arquivo
    não pode ser importado em teste automatizado (sempre tenta abrir a
    Picamera2). Se alguém corrigir isso, este teste vai FALHAR — é o sinal
    para remover/atualizar o teste e escrever a caracterização de verdade.
    """
    fonte = _fonte()
    assert 'if __name__ == "__main__"' not in fonte
    assert "if __name__ == '__main__'" not in fonte
