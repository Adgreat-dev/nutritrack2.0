import sys
import subprocess
import codecs

proc = subprocess.run(['python', 'debug_gemini.py'], capture_output=True)
stdout = proc.stdout.decode('cp1252', errors='replace')
stderr = proc.stderr.decode('cp1252', errors='replace')

with open('debug_output_4.txt', 'w', encoding='utf-8') as f:
    f.write(stdout + stderr)
