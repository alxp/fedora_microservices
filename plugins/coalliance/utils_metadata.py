import httplib
import string

#handle constants
handleServer='damocles.coalliance.org'
handleServerPort='9080'
handleServerApp='/handles/handle.jsp?'

def get_handle(obj):
    try:
      conn = httplib.HTTPConnection(handleServer,handleServerPort,timeout=10)
      conn.request('GET', handleServerApp+'debug=true&adr3=true&pid='+obj.pid)
      res = conn.getresponse()
    except:
      logging.error("Error connecting to Handle Server. PID: %s." % (obj.pid))
      return False

    # convert the response to lowercase and see if it contains success
    text = string.lower(res.read())

    if ( string.find(text,'==>success') != -1 ):
        logging.info("Successfuly created handle for %s." % obj.pid)
        return True
    else:
        logging.info("Failed to create handle for %s." % obj.pid)
        return False

def runRules(self, obj, dsid, body):

    self.obj = obj
    self.dsid = dsid
    try:
        if dsid == 'MODS':
            # some functions use the wrong namespace 
            # determine what to use
            mods_namespace = '{http://www.loc.gov/mods/v3}'

            parser = etree.XMLParser(remove_blank_text=True)
            root = etree.fromstring(obj['MODS'].getContent().read(), parser)

            ns = None

            for k in root.nsmap:
                if(type(k) == types.StringType and k.lower().find('mods') != -1):
                    ns = '{%s}' % root.nsmap[k]

            if ns == None:
                ns = mods_namespace

            url = root.find(ns+'location/'+ns+'url')
            if(url == None and get_handle(obj)):
                location = root.find(ns+'location')
                if(location == None):
                    location = etree.SubElement(root, ns+'location')
                url = etree.SubElement(location, ns+'url')
                url.attrib['usage']='primary display'
                url.text = 'http://hdl.handle.net/10176/'+obj.pid
                obj['MODS'].setContent(etree.tostring(root, pretty_print=True))
        else:
            self.relsint = RELSINTDatastream(obj)
            self.relationships = self.relsint.getRelationships(dsid)
            self.mimetype_dispatch()

        #TODO
        #handle MODS handle stuff 
    except FedoraConnectionException:
        logging.warning('Object %s does not exist.' % obj.pid)

