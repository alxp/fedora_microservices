'''
Created on Oct 19, 2010

@author: aoneill
'''
from categories import FedoraMicroService
import os, tempfile
from shutil import rmtree

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
    rmtree(d, ignore_errors = True)
    os.chdir(cwd)
    return obj

class islandora_strictpdf(FedoraMicroService):
    '''
    classdocs
    '''
    name = "PDF content model"
    content_model = "islandora:strict_pdf"
    dsIDs = ['OBJ']

    def runRules(self, obj, dsid):
        if dsid == 'OBJ':
            return create_pdf_thumbnail(obj)
        return obj

    def __init__(self):
        '''
        Constructor
        '''
        