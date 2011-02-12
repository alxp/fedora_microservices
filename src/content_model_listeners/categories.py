'''
Created on Oct 19, 2010

@author: aoneill
'''


import tempfile, os, subprocess, logging
from urllib import quote

def get_datastream_as_file(obj, dsid, extension = ''):
    d = tempfile.mkdtemp()
    success = False
    tries = 10
    filename = '%(dir)s/content.%(ext)s' % {'dir': d, 'ext': extension}
    while not success and tries > 0:
        f =open(filename, 'w')
        f.write(obj[dsid].getContent().read())
        os.fsync(f.fileno())
        f.close()
        logging.debug("Size of datastream: %(size)d. Size on disk: %(size_disk)d." % {'size': obj[dsid].size, 'size_disk': os.path.getsize(filename)})
        if os.path.getsize(filename) != obj[dsid].size:
            tries = tries - 1
        else:
            success = True
    return d, 'content.'+extension

def update_datastream(obj, dsid, filename, label='', mimeType='', controlGroup='M'): 
    # Using curl due to an incompatibility with the pyfcrepo library.
    conn = obj.client.api.connection 
    subprocess.call(['curl', '-i', '-H', '-XPOST', '%(url)s/objects/%(pid)s/datastreams/%(dsid)s?dsLabel=%(label)s&mimeType=%(mimetype)s&controlGroup=%(controlgroup)s'
                           % {'url': conn.url, 'pid': obj.pid, 'dsid': dsid, 'label': quote(label), 'mimetype': mimeType, 'controlgroup': controlGroup }, 
                           '-F', 'file=@%(filename)s' % {'filename': filename}, '-u', '%(username)s:%(password)s' % {'username': conn.username, 'password': conn.password}])

class FedoraMicroService(object):
    '''
    classdocs
    '''
    name = "Generic Microservice"
    content_model = "fedora-system:FedoraObject-3.0" 
    dsIDs = ['DC']    
    
    def runRules(self, obj, dsid, body):
        
        return 


    def __init__(self):
        '''
        Constructor
        '''
        