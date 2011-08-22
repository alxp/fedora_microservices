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
    logging.debug("Updating datastream:")
    conn = obj.client.api.connection

    try:
        logging.debug("using curl to update object %(obj)s, datastream %(dsid)s, from file %(file)s" % {'obj': obj, 'dsid': dsid, 'file': filename})
        r = subprocess.call(['curl', '-i', '-H', '-XPOST', '%(url)s/objects/%(pid)s/datastreams/%(dsid)s?dsLabel=%(label)s&mimeType=%(mimetype)s&controlGroup=%(controlgroup)s'
                           % {'url': conn.url, 'pid': obj.pid, 'dsid': dsid, 'label': quote(label), 'mimetype': mimeType, 'controlgroup': controlGroup }, 
                           '-F', 'file=@%(filename)s' % {'filename': filename}, '-u', '%(username)s:%(password)s' % {'username': conn.username, 'password': conn.password}])
    
        if not r == 0:
            logging.error("error in curl code %(code)s" % {'code': r})

    except Exception as e:
        logging.error('exception in curl call: ' + str(e))
        r = 1
    
    return r == 0
