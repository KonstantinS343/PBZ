object_property_template = {
    "type": "rdf:type",
    "range": "rdfs:range",
    "domain": "rdfs:domain",
    "ObjectProperty": "owl:ObjectProperty",
}


class_template = {
    "type": "rdf:type",
    "subClassOf": "rdfs:subClassOf",
    "Class": "owl:Class",
}


data_property_template = {
    "type": "rdf:type",
    "range": "rdfs:range",
    "domain": "rdfs:domain",
    "DatatypeProperty": "owl:DatatypeProperty",
    "decimal": "xsd:decimal",
    "int": "xsd:int",
    "string": "xsd:string",
}