import os
import sys

# Принудительно устанавливаем кодировку UTF-8 для всего Python
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

# Для Windows - устанавливаем кодовую страницу UTF-8
if sys.platform == "win32":
    os.system('chcp 65001 > nul')

print("Кодировка установлена на UTF-8")