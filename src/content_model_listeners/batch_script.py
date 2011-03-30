'''
Created on 2010-07-20

@author: al
'''
import fcrepo.connection, sys, logging
from fcrepo.client import FedoraClient
from fcrepo.utils import NS
from stomp.exception import NotConnectedException
from categories import FedoraMicroService

sys.path.append( 'plugins' )

from coalliance_coccOralHistoryCModel import coalliance_coccOralHistoryCModel

co = coalliance_coccOralHistoryCModel()

fedora_url = 'http://localhost:8080/fedora'
username = 'fedoraAdmin'
password = 'fedoraAdmin'
log_filename = 'script.log'

body = ''
pids = [
#pids to work on here
]

levels = {'DEBUG':logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR':logging
.ERROR, 'CRITICAL':logging.CRITICAL, 'FATAL':logging.FATAL}

logging.basicConfig(filename = log_filename, level = levels['INFO'])
fc = fcrepo.connection.Connection(fedora_url, username = username, password = password)
client = FedoraClient(fc)

for pid in pids:
    obj = client.getObject(pid)
    logging.info("Processing Pid: %s"%(obj.pid))
    for dsid in obj:
        co.runRules(obj, dsid, body)
