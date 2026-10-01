"""Fetch the pinned runtime and required wheels into an ignored test directory."""
import json
import sys
import urllib.request
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
destination=Path(sys.argv[1] if len(sys.argv)>1 else '.runtime')
destination.mkdir(parents=True,exist_ok=True)
base='https://cdn.jsdelivr.net/pyodide/v0.27.7/full/'
def fetch(name):
    target=destination/name
    if not target.exists():
        with urllib.request.urlopen(base+name,timeout=90) as response:
            target.write_bytes(response.read())
fetch('pyodide-lock.json')
lock=json.loads((destination/'pyodide-lock.json').read_text())
needed=set()
def include(name):
    if name in needed:return
    needed.add(name)
    for dependency in lock['packages'][name]['depends']:include(dependency)
for name in ['pandas','scipy','scikit-learn']:include(name)
files=['pyodide.js','pyodide.asm.js','pyodide.asm.wasm','python_stdlib.zip']+[lock['packages'][n]['file_name'] for n in needed]
with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(fetch,files))
print('Pinned browser runtime ready')
