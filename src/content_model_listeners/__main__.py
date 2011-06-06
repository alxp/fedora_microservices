'''
Created on 2010-07-20

@author: al
'''
import fcrepo.connection, time, ConfigParser, sys, feedparser, logging, os, signal, types, threading
from stomp.connect import Connection
from stomp.listener import ConnectionListener, StatsListener
from fcrepo.client import FedoraClient
from fcrepo.utils import NS
from stomp.exception import NotConnectedException, ReconnectFailedException
from optparse import OptionParser
from categories import FedoraMicroService
from yapsy.PluginManager import PluginManager
from fcrepo.connection import FedoraConnectionException

# Add the URI reference for Fedora content models to the available namespaces.
NS['fedoramodel'] = u"info:fedora/fedora-system:def/model#"

CONFIG_FILE_NAME = 'content_model_listener.cfg'

TOPIC_PREFIX = '/topic/fedora.contentmodel.'

class ContentModelListener(ConnectionListener):
    '''
    classdocs
    '''
    def __init__(self, content_models, host='localhost', port=61613, user='', passcode='', fedora_url=''):
        '''
        Constructor
        '''
        self.conn = Connection([(host, port)], user, passcode)
        self.conn.set_listener('', self)
        self.conn.start()
        logging.info('Connecting to STOMP server %(host)s on port %(port)s.' % {'host': host, 'port': port})
        self.transaction_id = None
        logging.info("Connecting to Fedora server at %(url)s" % {'url': fedora_url})
        self.fc = fcrepo.connection.Connection(fedora_url, username = user, password = passcode)
        self.client = FedoraClient(self.fc)
        self.fedora_url = fedora_url
        self.username = user
        self.password = passcode
        
        # Create plugin manager
        self.manager = PluginManager(categories_filter = {"FedoraMicroService": FedoraMicroService})
        plugin_path = os.path.dirname(__file__)
        self.manager.setPluginPlaces([plugin_path + "/plugins"])
        logging.debug("Plugin path: " + plugin_path + "/plugins")
        
        # Load plugins.
        self.manager.locatePlugins()
        self.manager.loadPlugins()
        self.contentModels = {}
        
        for plugin in self.manager.getPluginsOfCategory("FedoraMicroService"):
            # plugin.plugin_object is an instance of the plubin
            logging.info("Loading plugin: %(name)s for content model %(cmodel)s." % {'name': plugin.plugin_object.name, 'cmodel': plugin.plugin_object.content_model})
            plugin.plugin_object.config = config
            if type(plugin.plugin_object.content_model) == types.StringType:
                content_models = [plugin.plugin_object.content_model]
            else:
                content_models = plugin.plugin_object.content_model
            for content_model in content_models:
                if content_model in self.contentModels:
                    self.contentModels[content_model].append(plugin.plugin_object)
                else:
                    self.contentModels[content_model] = [plugin.plugin_object]
    
    def __print_async(self, frame_type, headers, body):
        """
        Utility function for printing messages.
        """
        #logging.debug("\r  \r", end='')
        logging.debug(frame_type)
        for header_key in headers.keys():
            logging.debug('%s: %s' % (header_key, headers[header_key]))
        logging.debug(body)
    
    def on_connecting(self, host_and_port):
        """
        \see ConnectionListener::on_connecting
        """
        self.conn.connect(wait=True)
        
    def on_disconnected(self):
        """
        \see ConnectionListener::on_disconnected
        """
        logging.error("lost connection reconnect in %d sec..." % reconnect_wait)
        signal.alarm(reconnect_wait)
        
    def on_message(self, headers, body):
        """
        \see ConnectionListener::on_message
        """ 
        global TOPIC_PREFIX
        self.__print_async('MESSAGE', headers, body)
        pid = headers['pid']
        dsid = headers['dsid']
        try:
            obj = self.client.getObject(pid)
            content_model = headers['destination'][len(TOPIC_PREFIX):]
            if content_model in self.contentModels:
                logging.info('Running rules for %(pid)s from %(cmodel)s.' % {'pid': obj.pid, 'cmodel': content_model} )
                for plugin in self.contentModels[content_model]: 
                    plugin.runRules(obj, dsid, body)
        except FedoraConnectionException:
            logging.warning('Object %s was not found.' % (pid))
        except:
            logging.exception('Uncaught exception in plugin!')

    def on_error(self, headers, body):
        """
        \see ConnectionListener::on_error
        """
        self.__print_async("ERROR", headers, body)
        logging.error("Error reported by stomp. Disconnect and try again.")
        self.disconnect('')
        signal.alarm(reconnect_wait)
        
    def on_connected(self, headers, body):
        """
        \see ConnectionListener::on_connected
        """
        global attempts
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
    
    def disconnect(self, args):
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
        self.fc = fcrepo.connection.Connection(self.fedora_url, username = self.username, password = self.password)
        self.client = FedoraClient(self.fc)
        

def reconnect_handler(signum, frame):
    global attempts
    try:
        logging.info("Attempt %d of %d." % (attempts+1, reconnect_max_attempts))
        sf.connect()
        logging.info("Reconnected.")
        for model in models:
            sf.subscribe("/topic/fedora.contentmodel.%s" % (model))
            logging.info("Subscribing to topic /topic/fedora.contentmodel.%(model)s." % {'model': model})
        signal.pause()

    except ReconnectFailedException:
        attempts = attempts + 1
        if(attempts == reconnect_max_attempts):
            logging.info("Unable to reconnect, shutting down")
            sys.exit(1)
        else:
            signal.alarm(reconnect_wait)
            signal.pause()
        
def shutdown_handler(signum, frame):
    sf.disconnect('');
    sys.exit(0);

def stomp_handler(signum, frame):
    if(stompthread.is_alive()):
        signal.pause()
    else:
        sys.exit(-1);

if __name__ == '__main__':
    config = ConfigParser.ConfigParser()
    parser = OptionParser()
    parser.add_option('-C', '--config-file', type = 'string', dest = 'configfile', default = CONFIG_FILE_NAME,
                      help = 'Path of the configuration file for this listener process instance.')
    
    (options, args) = parser.parse_args()
    
    if os.path.exists(options.configfile):
        config.read(options.configfile)
    else:
        print 'Config file %s not found!' % (options.configfile)
        sys.exit(1)

    # register handlers so we properly disconnect and reconnect
    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)
    signal.signal(signal.SIGALRM, reconnect_handler)
    signal.signal(signal.SIGVTALRM, stomp_handler)

    #defined for the reconnect handler above
    attempts = 0
    reconnect_attempts = 0
    reconnect_max_attempts = int(config.get('Reconnect', 'tries'))
    reconnect_wait = int(config.get('Reconnect', 'wait'))
            
    log_filename = config.get('Logging', 'log_file')
    levels = {'DEBUG':logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR':logging.ERROR, 'CRITICAL':logging.CRITICAL, 'FATAL':logging.FATAL}
    logging_format = '%(asctime)s : %(levelname)s : %(name)s : %(message)s'
    date_format = '(%m/%d/%y)%H:%M:%S'
    logging.basicConfig(filename = log_filename, level = levels[config.get('Logging', 'log_level')], format=logging_format, datefmt=date_format)

    models = [v.strip() for v in config.get('ContentModels', 'models').split(',')]
    messaging_host = config.get('MessagingServer', 'hostname')
    messaging_port = int(config.get('MessagingServer', 'port'))
    messaging_user = config.get('MessagingServer', 'username')
    messaging_pass = config.get('MessagingServer', 'password')
    repository_url = config.get('RepositoryServer', 'url')
 
    try:
        sf = ContentModelListener(models, messaging_host, messaging_port, messaging_user, messaging_pass, repository_url)

    except ReconnectFailedException:
        logging.info('Failed to connect to server: %s:%d' % (options.host,options.port))
        print 'Failed to connect to server: %s:%d' % (options.host, options.port)
        #just exist
        sys.exit(-1);

    for model in models:
        sf.subscribe("/topic/fedora.contentmodel.%s" % (model))
        logging.info("Subscribing to topic /topic/fedora.contentmodel.%(model)s." % {'model': model})

    #wait for a signal
    signal.pause()
