import os
import io
import subprocess
import os
from time import sleep

def update():
    try:
        proc = subprocess.Popen(['stat', 'report.tex'], stdout=subprocess.PIPE)
        out = proc.stdout.read()
        pos = out.find("Modify")
        stream = io.TextIOWrapper(io.BytesIO(out))
        stream.seek(pos)
    except:
        pass
    return stream.readline()

print "Watching on report.tex..."
prevline = update()
while 1:
    currentline = update()
    if prevline != currentline:
        os.system('pdflatex report.tex > /dev/null')
        prevline = currentline
    sleep(0.1)
