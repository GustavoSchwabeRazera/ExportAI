from pathlib import Path
import subprocess
import sys

BACKEND = Path(__file__).resolve().parents[1]


def test_arquivos_de_deploy_existem():
    for nome in [
        "Dockerfile",
        ".dockerignore",
        "docker-compose.yml",
        ".env.production.example",
        "start.py",
    ]:
        assert (BACKEND / nome).exists(), nome


def test_start_compila():
    resultado = subprocess.run(
        [sys.executable, "-m", "py_compile", str(BACKEND / "start.py")],
        capture_output=True,
        text=True,
    )
    assert resultado.returncode == 0, resultado.stderr


def test_dockerfile_nao_executa_com_root():
    conteudo = (BACKEND / "Dockerfile").read_text(encoding="utf-8")
    assert "USER exportai" in conteudo
    assert "HEALTHCHECK" in conteudo
    assert "--host 0.0.0.0" in conteudo
    assert "--port ${PORT}" in conteudo


def test_dockerignore_protege_arquivos_locais():
    conteudo = (BACKEND / ".dockerignore").read_text(encoding="utf-8")
    assert ".env" in conteudo
    assert ".venv" in conteudo
    assert "tests" in conteudo
