import ConfigParser
import sys
import logging
import logging.handlers
import fcrepo.connection
import os
import signal
import json
from datetime import datetime
from xml.etree import ElementTree
from stomp.connect import Connection
from stomp.listener import ConnectionListener
from fcrepo.client import FedoraClient
from fcrepo.utils import NS
from stomp.exception import NotConnectedException, ReconnectFailedException
from optparse import OptionParser
from fcrepo.connection import FedoraConnectionException
from plugin_manager import IslandoraListenerPlugin, IslandoraFilteredPluginManager, IslandoraPluginManager

# Add the URI reference for Fedora content models to the available namespaces.
NS['fedoramodel'] = u"info:fedora/fedora-system:def/model#"

CONFIG_FILE_NAME = 'islandora_listener.cfg'

# the topics to listen on
ISLANDORA_TOPIC = '/topic/islandora'
FEDORA_TOPIC = '/topic/fedora.apim.update'

# timer for stomp
POLLING_TIME = 20

class IslandoraListener(ConnectionListener):

    def __init__(self, repository_url, repository_user, repository_pass, plugin_manager, host='localhost', port=61613):
        
        # connect to the stomp listener
        try:
            self.conn = Connection([(host, port)])
            self.conn.set_listener('', self)
            self.conn.start()
        except ReconnectFailedException, e:
            message = 'Failed to connect to server: %(host)s:%(port)d. Error: %(error)s.' % {'host':host,'port':port,'error':e}
            logger.info(message)
            print message
            sys.exit(1)

        # connect to the fedora server
        try:
            logger.info("Connecting to Fedora server at %(url)s" % {'url': repository_url})
            self.fc = fcrepo.connection.Connection(repository_url, username = repository_user, password = repository_pass, persistent=False)
            self.client = FedoraClient(self.fc)
        except Exception,e:
            logger.error('Error while connecting to Fedora server %(url)s. Error: (%(error)s).' % {'url':repository_url, 'error':e})
            try:
                self.conn.disconnect()
            except NotConnectedException:
                pass
            sys.exit(1)

        self.transaction_id = None

        logger.info('Connecting to STOMP server %(host)s on port %(port)s.' % {'host': host, 'port': port})

        self.manager = plugin_manager
        self.repository_url = repository_url
        self.repository_user = repository_user
        self.repository_pass = repository_pass

        self.host = host
        self.port = port
    
    def __print_async(self, frame_type, headers, body):
        """
        Utility function for printing messages.
        """
        slogger = logging.getLogger('IslandoraListener:Stomp')
        slogger.debug(frame_type)
        for header_key in headers.keys():
            slogger.debug('%s: %s' % (header_key, headers[header_key]))
        slogger.debug(body)
    
    def on_connecting(self, host_and_port):
        """
        \see ConnectionListener::on_connecting
        """
        self.conn.connect(wait=True)
        
    def on_disconnected(self):
        """
        \see ConnectionListener::on_disconnected
        """
        global disconnected_state
        logger.error("lost connection reconnect in %d sec..." % reconnect_wait)
        signal.alarm(reconnect_wait)
        disconnected_state = True

    def _process_fedora_message(self, message):
        etree = ElementTree.ElementTree()
        root = ElementTree.XML(message)
        ds = {}

        ATOM_NS = "{http://www.w3.org/2005/Atom}"
        FEDORA_NS = "{http://www.fedora.info/definitions/1/0/types/}"
        FEDORA_VERSION = 'info:fedora/fedora-system:def/view#version'

        ds['id'] = root.find(ATOM_NS+'id').text
        updated = root.find(ATOM_NS+'updated').text
        ds['updated'] = datetime.strptime(updated, '%Y-%m-%dT%H:%M:%S.%fZ')
        ds['author'] = root.find(ATOM_NS+'author/'+ATOM_NS+'name').text
        ds['uri'] = root.find(ATOM_NS+'author/'+ATOM_NS+'uri').text
        ds['method'] = root.find(ATOM_NS+'title').text
        ds['args'] = []
        ds['dsid'] = None

        for arg in root.findall(ATOM_NS+'category'):
            scheme = arg.get('scheme').split(':',1)
            if scheme[0] == 'fedora-types':
                r = {}
                r['name'] = arg.get('scheme').split(':',1)[1]
                r['type'] = arg.get('label').split(':',1)[1]
                r['value'] = arg.get('term')
                if r['name'] == 'dsID':
                    ds['dsid'] = r['value']
                ds['args'].append(r)
            elif scheme[0] == FEDORA_VERSION:
                ds['fedora_version'] = arg.get('term')

        pid = root.find(ATOM_NS+'summary')
        if pid == None:
            ds['pid'] = None
        else:
            ds['pid'] = pid.text

        ds['return'] = root.find(ATOM_NS+'content').text

        return ds

    def _get_fedora_content_models(self, obj):
            if obj != None and 'RELS-EXT' in obj:
                ds = obj['RELS-EXT']
                content_models = [elem['value'].split('/')[1] for elem in ds[NS.fedoramodel.hasModel]]
            else:
                content_models = []

            return content_models

    def on_message(self, headers, body):
        """
        \see ConnectionListener::on_message
        """ 
        self.__print_async('MESSAGE', headers, body)

        # pivot on the message type
        if headers['destination'] == ISLANDORA_TOPIC:
            method = headers['method']

            if method in islandora_methods:
                plugin_set = islandora_methods['all'] | islandora_methods[method]
            else:
                plugin_set = islandora_methods['all']

            for plugin in plugin_set:
                try:
                    message = json.loads(body)
                    plugin.plugin_object.islandoraMessage(method, message, self.client)
                except:
                    logger.exception('Uncaught exception in plugin: %s!' % plugin.name)

        elif headers['destination'] == FEDORA_TOPIC:
            pid = headers['pid']
            method = headers['methodName']
            message = self._process_fedora_message(body)
            
            # try to get fedora object, it could not exist
            try:
                obj = self.client.getObject(pid)
            except FedoraConnectionException:
                obj = None

            content_models = self._get_fedora_content_models(obj)

            # add the content models to the message object for the plugin
            message['content_models'] = content_models

            plugin_set_methods = fedora_methods['all'].copy()
            if method in fedora_methods:
                plugin_set_methods |= fedora_methods[method]

            plugin_set_cm = fedora_content_models['all'].copy()
            for cm in content_models:
                if cm in fedora_content_models:
                    plugin_set_cm |= fedora_content_models[cm]

            for plugin in (plugin_set_cm & plugin_set_methods):
                try:
                    plugin.plugin_object.fedoraMessage(message, obj, self.client)
                except:
                    logger.exception('Uncaught exception in plugin: %s!' % plugin.name)

    def on_error(self, headers, body):
        """
        \see ConnectionListener::on_error
        """
        logger.error("Error reported by Stomp. Shutting down.")
        logger.error(body)
        self.disconnect()
        os._exit(1)

# broken code to retry on error, when we have an unstable server
# i think its worth fixing this code, currently its hard to test because
# this only happens sometimes
#    def on_error(self, headers, body):
#        """
#        \see ConnectionListener::on_error
#        """
#        global disconnected_state
#        disconnected_state = True
#        logger.error("Error reported by Stomp. Trying to reconnect.")
#        logger.error(body)
#        logger.debug('here')
#        self.conn.stop()
#        logger.debug('there')
#        signal.alarm(reconnect_wait)
        
    def on_connected(self, headers, body):
        """
        \see ConnectionListener::on_connected
        """
        global attempts
        global disconnected_state
        disconnected_state = False
        signal.alarm(POLLING_TIME)
        attempts = 0
        self.__print_async("CONNECTED", headers, body)
        
    def ack(self, args):
        """
        Required Parameters:
            message-id - the id of the message being acknowledged
        
        Description:
            Acknowledge consumption of a message from a subscription using client
            acknowledgement. When a client has issued a subscribe with an 'ack' flag set to client
            received from that destination will not be considered to have been consumed  (by the server) until
            the message has been acknowledged.
        """
        if not self.transaction_id:
            self.conn.ack(headers = { 'message-id' : args[1]})
        else:
            self.conn.ack(headers = { 'message-id' : args[1]}, transaction=self.transaction_id)
        
    def abort(self, args):
        """
        Description:
            Roll back a transaction in progress.
        """
        if self.transaction_id:
            self.conn.abort(transaction=self.transaction_id)
            self.transaction_id = None
    
    def begin(self, args):
        """
        Description
            Start a transaction. Transactions in this case apply to sending and acknowledging
            any messages sent or acknowledged during a transaction will be handled atomically based on teh
            transaction.
        """
        if not self.transaction_id:
            self.transaction_id = self.conn.begin()
    
    def commit(self, args):
        """
        Description:
            Commit a transaction in progress.
        """
        if self.transaction_id:
            self.conn.commit(transaction=self.transaction_id)
            self.transaction_id = None
    
    def disconnect(self):
        """
        Description:
            Gracefully disconnect from the server.
        """
        try:
            self.conn.disconnect()
        except NotConnectedException:
            pass
    
    def send(self, destination, correlation_id, message):
        """
        Required Parametes:
            destination - where to send the message
            message - the content to send
            
        Description:
        Sends a message to a destination in the message system.
        """
        self.conn.send(destination=destination, message=message, headers={'correlation-id': correlation_id})
        
    def subscribe(self, destination, ack='auto'):
        """
        Required Parameters:
            destination - the name to subscribe to
            
        Optional Parameters:
            ack - how to handle acknowledgements for a message, either automatically (auto) or manually (client)
            
        Description
            Register to listen to a given destination. Like send, the subscribe command requires a destination
            header indicating which destination to subscribe to.  The ack parameter is optional, and defaults to auto.
        """
        self.conn.subscribe(destination=destination, ack=ack)
        
    def unsubscribe(self, destination):
        """
        Required Parameters:
            destination - the name to unsubscribe from
        
        Description:
            Remove an existing subscription - so that the client no longer receives messages from that destination.
        """
        self.conn.unsubscribe(destination)

    def connect(self):
        self.conn.start()
        self.fc = fcrepo.connection.Connection(repository_url, username = repository_user, password = repository_pass)
        self.client = FedoraClient(self.fc)
        

def alarm_handler(signum, frame):
    if disconnected_state == True:
        global attempts
        try:
            logger.info("Attempt %d of %d." % (attempts+1, reconnect_max_attempts))
            stomp_client.connect()

            stomp_client.subscribe(ISLANDORA_TOPIC)
            stomp_client.subscribe(FEDORA_TOPIC)

        except ReconnectFailedException:
            attempts = attempts + 1
            if(attempts == reconnect_max_attempts):
                logger.error("Unable to reconnect, shutting down")
                sys.exit(1)
            else:
                signal.alarm(reconnect_wait)
    else:
        if stomp_client.conn.is_connected():
            signal.alarm(POLLING_TIME)
        else:
            sys.exit(1)
        

        
def shutdown_handler(signum, frame):

    stomp_client.disconnect();
    sys.exit(0);

if __name__ == '__main__':

    # parse the passed in command line options
    # and read the passed in config file if it exists
    configp = ConfigParser.SafeConfigParser()
    optionp = OptionParser()

    optionp.add_option('-C', '--config-file', type = 'string', dest = 'configfile', default = CONFIG_FILE_NAME,
                  help = 'Path of the configuration file for this listener process instance.')
    optionp.add_option('-P', '--plugin-path', type = 'string', dest = 'pluginpath',
                  help = 'Path to a directory with plugin files.')
    
    (options, args) = optionp.parse_args()
    
    if os.path.exists(options.configfile):
        try:
            configp.read(options.configfile)
        except ConfigParser.MissingSectionHeaderError, e:
            print 'Malformed Config File'
            print e
            sys.exit(1)
    else:
        print 'Config file %s not found!' % (options.configfile)
        optionp.print_help()
        sys.exit(1)

    # load config file values and give error if its incorrect
    try:
        #messaging server
        messaging_host = configp.get('MessagingServer', 'hostname')
        messaging_port = configp.getint('MessagingServer', 'port')

        #reconnect
        reconnect_max_attempts = configp.getint('Reconnect', 'tries')
        reconnect_wait = configp.getint('Reconnect', 'wait')

        #repository server
        repository_user = configp.get('RepositoryServer', 'username')
        repository_pass = configp.get('RepositoryServer', 'password')
        repository_url = configp.get('RepositoryServer', 'url')

        #logging
        log_filename = configp.get('Logging', 'file')
        log_level = configp.get('Logging', 'level')
        log_max_size = configp.getint('Logging','max_size')
        log_backup = configp.getint('Logging','backup')

        #plugins
        plugins_enabled = [v.strip() for v in configp.get('Plugins', 'enabled').split(',')]

    except (ConfigParser.NoOptionError, ConfigParser.NoSectionError), e:
        print 'Error reading config file %s' % options.configfile
        print e
        sys.exit(1)

    # register handlers so we properly disconnect and reconnect
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGALRM, alarm_handler)

    # global defined for the reconnect handler above
    attempts = 0

    # setup logging
    levels = {'DEBUG':logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING,
      'ERROR':logging.ERROR, 'CRITICAL':logging.CRITICAL, 'FATAL':logging.FATAL}
    logging_format = '%(asctime)s %(levelname)s %(name)s %(message)s'
    date_format = '[%b/%d/%Y:%H:%M:%S]'
    log_handler = logging.handlers.RotatingFileHandler(log_filename, maxBytes=log_max_size, backupCount=log_backup)
    log_formatter = logging.Formatter(logging_format, date_format)
    log_handler.setFormatter(log_formatter)
    root_logger = logging.getLogger()
    root_logger.addHandler(log_handler)
    root_logger.setLevel(levels[log_level])
    logger = logging.getLogger('IslandoraListener')

    # setup plugin manager and load plugins
    plugin_path = [os.path.join(os.path.dirname(__file__),'plugins')]
    if options.pluginpath:
        plugin_path.extend([v.strip() for v in options.pluginpath.split(',')])
    logger.info("Plugin path: %s" % plugin_path)
    categories_filter = {"IslandoraListenerPluginPlugin": IslandoraListenerPlugin}
    plugin_extension = 'cfg'
    manager = IslandoraPluginManager(categories_filter, plugin_path, plugin_extension)
    manager = IslandoraFilteredPluginManager(plugins_enabled, manager)
    manager.collectPlugins()
    plugins = manager.getAllPlugins()
    if len(plugins) == 0:
        logger.error('No eligible plugins loaded. Exiting.')
        sys.exit(1)

    #setup plugin datastructures
    islandora_methods = {'all':set()}
    fedora_methods = {'all':set()}
    fedora_content_models = {'all':set()}
    for plugin in plugins:
        for method in plugin.islandora_methods:
            if method != '':
                if method not in islandora_methods:
                    islandora_methods[method] = set()
                islandora_methods[method].add(plugin)
        for method in plugin.fedora_methods:
            if method != '':
                if method not in fedora_methods:
                    fedora_methods[method] = set()
                fedora_methods[method].add(plugin)
        for cm in plugin.fedora_content_models:
            if cm != '':
                if cm not in fedora_content_models:
                    fedora_content_models[cm] = set()
                fedora_content_models[cm].add(plugin)

    # this if for the watchdog timer, watching if stomp exits behind our back
    disconnected_state = False

    #connect to stomp and fedora servers
    stomp_client = IslandoraListener(repository_url, repository_user, repository_pass, manager, messaging_host, messaging_port)

    stomp_client.subscribe(ISLANDORA_TOPIC)
    stomp_client.subscribe(FEDORA_TOPIC)

    # wait for a signal
    while(True):
        signal.pause()
