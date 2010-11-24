'''
Created on 2010-07-19

@author: aoneill
'''

import tempfile, os
import fcrepo.connection
from fcrepo.client import FedoraClient
from fcrepo.utils import NS

def create_pdf_thumbnail(obj):
    """
    Create a thumbnail of a STRICT_PDF object's PDF stream and add it to the Fedora object.
    """
    d = tempfile.mkdtemp()
    cwd = os.getcwd()
    os.chdir(d)
    f = open(d+'/tmpfile.pdf', 'w')
    f.write(obj['OBJ'].getContent().read())
    f.close()
    
    os.system('sips -s format jpeg \"tmpfile.pdf\" -z 150 150 --out \"tmpfile.jpg\" >/dev/null')
    tnfile = open(d+'/tmpfile.jpg', 'r')
    if 'TN' not in obj:
        obj.addDatastream('TN')
    obj['TN'].setContent(tnfile)
    tnfile.close()
    os.remove(d+'/tmpfile.pdf')
    os.remove(d+'/tmpfile.jpg')
    os.chdir(cwd)
    return obj