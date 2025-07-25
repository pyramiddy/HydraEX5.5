import subprocess
import sys

def instalar_pacote(pacote):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pacote])

try:
    import openpyxl
except ImportError:
    print("openpyxl não encontrado. Instalando...")
    instalar_pacote("openpyxl")
    print("openpyxl instalado com sucesso.")