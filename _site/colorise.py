import fileinput
import sys
import re

def span(match):
    arg = match.group(1)
    if arg == 'end':
        return '</span>'
    else:
        return '<span class="{}">'.format(arg)
    
for line in fileinput.input(inplace=True, backup='.bak'):
    print re.sub('<span class="s">"!!([^!]*)!!"</span>', span, line.rstrip())
