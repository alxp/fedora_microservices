from xml.dom.minidom import Document, parse, parseString;
from xml.dom import Node
import fcrepo;

class RELSINTDatastream():

    def __init__(self, obj):
        #if relsint doesn't exist create it
        if 'RELS-INT' not in obj:
            doc = Document();
            rdf = doc.createElement('rdf:RDF')
            rdf.setAttribute('xmlns:rdf', 'http://www.w3.org/1999/02/22-rdf-syntax-ns#')
            rdf.setAttribute('xmlns:rdfs', 'http://www.w3.org/2000/01/rdf-schema#')
            rdf.setAttribute('xmlns:fedora', 'info:fedora/fedora-system:def/relations-external#')
            rdf.setAttribute('xmlns:coal', 'http://www.coalliance.org/ontologies/relsint')
            doc.appendChild(rdf)
            obj.addDataStream('RELS-INT', doc.toprettyxml())
        else:
            doc = parseString(obj['RELS-INT'].getContent().read())

        self.obj = obj
        self.doc = doc

    def addRelationship( self, subject, predicate, object ):
        elements = self.doc.getElementsByTagName('rdf:RDF')
        rdf = elements[0]

        descriptions = rdf.getElementsByTagName('rdf:Description')
        description = None

        for desc in descriptions:
            if (desc.getAttribute('rdf:about') == 'info:fedora/'+self.obj.pid+'/'+subject):
                description = desc

        if not description: 
            description = self.doc.createElement("rdf:Description")
            description.setAttribute('rdf:about', 'info:fedora/'+self.obj.pid+'/'+subject)
            rdf.appendChild(description)

        element = self.doc.createElement('coal:'+predicate)
        element.setAttribute('rdf:resource','info:fedora/'+self.obj.pid+'/'+object)
        description.appendChild(element)

    def addRelationshipLiteral( self, subject, predicate, literal ):
        elements = self.doc.getElementsByTagName('rdf:RDF')
        rdf = elements[0]

        descriptions = rdf.getElementsByTagName('rdf:Description')
        description = None

        for desc in descriptions:
            if (desc.getAttribute('rdf:about') == 'info:fedora/'+self.obj.pid+'/'+subject):
                description = desc

        if not description: 
            description = self.doc.createElement("rdf:Description")
            description.setAttribute('rdf:about', 'info:fedora/'+self.obj.pid+'/'+subject)
            rdf.appendChild(description)

        element = self.doc.createElement('coal:'+predicate)
        description.appendChild(element)
        literal = self.doc.createTextNode(literal)
        element.appendChild(literal)

    def getRelationships( self, subject ):
        elements = self.doc.getElementsByTagName('rdf:RDF')
        rdf = elements[0]

        relationships = {}

        descriptions = rdf.getElementsByTagName('rdf:Description')
        for description in descriptions:
            if (description.getAttribute('rdf:about') == 'info:fedora/'+self.obj.pid+'/'+subject):
                for element in description.childNodes:
                    if( element.nodeType == Node.ELEMENT_NODE ):
                        predicate = element.tagName.rsplit(':',1)[1]
                        if predicate not in relationships:
                            relationships[predicate] = []
                        if element.hasAttribute('rdf:resource'):
                            resource = element.getAttribute('rdf:resource')
                            resource = resource.rsplit('/',1)[1]
                            relationships[predicate].append(resource)
                        else:
                            relationships[predicate].append(element.childNodes[0].nodeValue)

        return relationships

    def update( self ):
        self.obj['RELS-INT'].setContent( self.doc.toxml() )
