import httplib
import string
import types
import logging
from lxml import etree

from islandoraUtils.metadata.fedora_relationships import rels_namespace, rels_object, rels_ext
from islandoraUtils.xacml.tools import Xacml
from islandoraUtils.xacml.exception import XacmlException

#handle constants
handleServer='damocles.coalliance.org'
handleServerPort='9080'
handleServerApp='/handles/handle.jsp?'

def get_handle(obj):
    logger = logging.getLogger('IslandoraListener.coalliance.get_handle')    
    try:
      conn = httplib.HTTPConnection(handleServer,handleServerPort,timeout=10)
      conn.request('GET', handleServerApp+'debug=true&adr3=true&pid='+obj.pid)
      res = conn.getresponse()
    except:
      logger.error("Error connecting to Handle Server. PID: %s." % (obj.pid))
      return False

    # convert the response to lowercase and see if it contains success
    text = string.lower(res.read())

    if ( string.find(text,'==>success') != -1 ):
        logger.info("Successfuly created handle for %s." % obj.pid)
        return True
    elif ( string.find(text,'handle already exists') != -1 ):
        logger.info("Handle already exists for %s." % obj.pid)
        return True
    else:
        logger.info("Failed to create handle for %s." % obj.pid)
        return False

def add_handle_to_mods(obj):

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

def add_policy_to_rels(obj):
    policy_ds = obj['POLICY']
    try:
        xacml = Xacml(policy_ds.getContent().read())
    except XacmlException:
        return False

    relsext = rels_ext(obj, rels_namespace('isle','http://islandora.ca/ontology/relsext'), 'isle')
    users = xacml.viewingRule.getUsers()
    roles = xacml.viewingRule.getRoles()
    for user in users:
        relsext.addRelationship('isViewableByUser', rels_object(user,rels_object.LITERAL))
    for role in roles:
        relsext.addRelationship('isViewableByRole', rels_object(role,rels_object.LITERAL))
    relsext.update()
