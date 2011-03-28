'''
Created on 2010-07-12

@author: Alexander O'Neill
'''


import signal, sys, time, ConfigParser, feedparser, logging, fcrepo.connection, os
from optparse import OptionParser
from stomp.connect import Connection
from stomp.listener import ConnectionListener, StatsListener
from stomp.exception import NotConnectedException
from fcrepo.client import FedoraClient
from fcrepo.utils import NS

# Add the URI reference for Fedora content models to the available namespaces.
NS['fedoramodel'] = u"info:fedora/fedora-system:def/model#"
CONFIG_FILE_NAME = 'fedora_listener.cfg'

class StompFedora(ConnectionListener):
    """
    A custom interface to the stomp.py client. See \link stomp::internal::connect::Connection \endlink
    for more information on establishing a connection to a stomp server.
    """
    def __init__(self, host='localhost', port=61613, user='', passcode='', fedora_url=''):
        self.conn = Connection([(host, port)], user, passcode)
        self.conn.set_listener('', self)
        self.conn.start()
        self.transaction_id = None
        self.fc = fcrepo.connection.Connection(fedora_url, username = user, password = passcode)
        self.client = FedoraClient(self.fc)
        
    def __print_async(self, frame_type, headers, body):
        """
        Utility function for printing messages.
        """
        logging.debug(frame_type)
        for header_key in headers.keys():
            logging.debug('%s: %s' % (header_key, headers[header_key]))
        logging.debug(body)
    
    def __get_content_models(self, pid):
        """
        Get a list of content models that apply to the object.
        """
        obj = self.client.getObject(pid)
        if 'RELS-EXT' in obj:
            ds = obj['RELS-EXT']
            return obj, [elem['value'].split('/')[1] for elem in ds[NS.fedoramodel.hasModel]]
        else:
            return obj, []
        
    def on_connecting(self, host_and_port):
        """
        \see ConnectionListener::on_connecting
        """
        self.conn.connect(wait=True)
        
    def on_disconnected(self):
        """
        \see ConnectionListener::on_disconnected
        """
        sysout("lost connection")
        
    def on_message(self, headers, body):
        """
        \see ConnectionListener::on_message
        """
        self.__print_async("MESSSAGE", headers, body)
        method = headers['methodName']
        pid = headers['pid']

        newheaders = { 'methodname':headers['methodName'], 'pid':headers['pid']}

        if method in ['addDatastream', 'modifyDatastreamByValue', 'modifyDatastreamByReference', 'modifyObject']:
            f = feedparser.parse(body)
            tags = f['entries'][0]['tags']
            dsids = [tag['term'] for tag in tags if tag['scheme'] == 'fedora-types:dsID']
            dsid = ''
            if dsids:
                dsid = dsids[0]
            newheaders['dsid'] = dsid
            obj, content_models = self.__get_content_models(pid) # and 'OBJ' in dsIDs:
            for content_model in content_models:
                print "/topic/fedora.contentmodel.%s %s" % (content_model, dsid)
                self.send("/topic/fedora.contentmodel.%s" % content_model, newheaders, body)
        elif method in ['ingest']:
            obj, content_models = self.__get_content_models(pid)
            for dsid in obj:
                for content_model in content_models:
                    newheaders['dsid'] = dsid
                    print "/topic/fedora.contentmodel.%s %s" % (content_model, dsid)
                    self.send("/topic/fedora.contentmodel.%s" % content_model, newheaders, body)
        
    def on_error(self, headers, body):
        """
        \see ConnectionListener::on_error
        """
        self.__print_async("ERROR", headers, body)
        
    def on_connected(self, headers, body):
        """
        \see ConnectionListener::on_connected
        """
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
    
    def send(self, destination, headers, message):
        """
        Required Parametes:
            destination - where to send the message
            message - the content to send
            
        Description:
        Sends a message to a destination in the message system.
        """
        self.conn.send(destination=destination, message=message, headers=headers)
        
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

def sighandler(signum, frame):
    sf.disconnect('');
    sys.exit(0);

if __name__ == '__main__':
    config = ConfigParser.ConfigParser({'hostname': 'localhost', 'port': '61613', 'username': 'fedoraAdmin', 'password': 'fedoraAdmin',
                                                      'log_file': 'fedora_listener.log', 'log_level': 'INFO',
                                                      'url': 'http://localhost:8080/fedora'})
    
    signal.signal(signal.SIGINT, sighandler);

    if os.path.exists(CONFIG_FILE_NAME):
        config.read(CONFIG_FILE_NAME)
    if os.path.exists('/etc/%(conf)s' % {'conf': CONFIG_FILE_NAME}):
        config.read('/etc/%(conf)s' % {'conf': CONFIG_FILE_NAME})
    if os.path.exists(os.path.expanduser('~/.fedora_microservices/%(conf)s' % {'conf': CONFIG_FILE_NAME})):
        config.read('/etc/%(conf)s' % {'conf': CONFIG_FILE_NAME})
    
    levels = {'DEBUG':logging.DEBUG, 'INFO': logging.INFO, 'WARNING': logging.WARNING, 'ERROR':logging.ERROR, 'CRITICAL':logging.CRITICAL, 'FATAL':logging.FATAL}
    logging.basicConfig(filename = config.get('Logging', 'log_file'), level = levels[config.get('Logging', 'log_level')])

    parser = OptionParser()
    
    parser.add_option('-H', '--host', type = 'string', dest = 'host', default = config.get('MessagingServer', 'hostname'),
                      help = 'Hostname or IP to connect to. Defaults to localhost if not specified.')
    parser.add_option('-P', '--port', type = int, dest = 'port', default = config.get('MessagingServer', 'port'),
                      help = 'Port providing stomp protocol connections. Defaults to 61613 if not specified.')
    parser.add_option('-U', '--user', type = 'string', dest = 'user', default = config.get('MessagingServer', 'username'),
                      help = 'Username for the connection')
    parser.add_option('-W', '--password', type = 'string', dest = 'password', default = config.get('MessagingServer', 'password'),
                      help = 'Password for the connection')
    parser.add_option('-R', '--fedoraurl', type = 'string', dest = 'fedoraurl', default = config.get('RepositoryServer', 'url'),
                      help = 'Fedora URL. Defaults to http://localhost:8080/fedora')
    
    (options, args) = parser.parse_args()
    sf = StompFedora(options.host, options.port, options.user, options.password, options.fedoraurl)

    sf.subscribe('/topic/fedora.apim.update')

    signal.pause();
