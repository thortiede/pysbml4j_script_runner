import os
import sys

from pysbml4j import Sbml4j
from pysbml4j import Configuration

import logging
from logging.config import fileConfig
import configparser

import xml.etree.ElementTree as ET

# global definitions for the log-config
configFolder = "/config"
fileConfig('{}/config.ini'.format(configFolder))
logger = logging.getLogger()
logging.getLogger("chardet.charsetprober").disabled = True

# global definition for the sbml4j-config
config = configparser.ConfigParser()
config.read('{}/config.ini'.format(configFolder))

def init_sbml4j(user=None):

    server_conf = config['server']
    host = server_conf.get('host')
    if not host.startswith('http'):
        host = "{}{}".format("http://", host)
    if user != None:
        client = Sbml4j(Configuration(host, server_conf.get('port'), server_conf.get('application_context'), user=user))
        return client
    else:
        client = Sbml4j(Configuration(host, server_conf.get('port'), server_conf.get('application_context')))
        return client

def get_key_mapping(root):
    key_mapping = {}
    for child in root.iter('{http://graphml.graphdrawing.org/xmlns}key'):
        #print(child.tag, child.attrib)
        #print(child.attrib['attr.name'])
        key_mapping[child.attrib['id']] = child.attrib['attr.name']
    return key_mapping

def get_node_data_elements(node_object, key_mapping, name_to_type_map):
    node_attribute_map = {}
    for data in node_object.iter('{http://graphml.graphdrawing.org/xmlns}data'):
        data_name = key_mapping[data.attrib['key']]
        if data_name in name_to_type_map:
            data_type = name_to_type_map[data_name]
            if data_type == 'double' or data_type == 'float':
                node_attribute_map[data_name] = float(data.text)
            else:
                node_attribute_map[data_name] = data.text
        else:
            node_attribute_map[data_name] = data.text
    return node_attribute_map

def get_id_to_symbol_map(root, key_mapping):
    id_to_symbol_map = {}
    for graph in root.iter('{http://graphml.graphdrawing.org/xmlns}graph'):
        for child in graph.iter('{http://graphml.graphdrawing.org/xmlns}node'):
            for attr in child.iter('{http://graphml.graphdrawing.org/xmlns}data'):
                if key_mapping[attr.attrib['key']] == 'symbol':
                    id_to_symbol_map[child.attrib['id']] = attr.text

    return id_to_symbol_map

def get_boolean_true_annotation_object(name, node_symbols):
    annotation_object = {}
    annotation_object['nodeAnnotationName'] = name
    node_annotation_dict = {}
    for node_symbol in node_symbols:
        node_annotation_dict[node_symbol] = True

    annotation_object['nodeAnnotation'] = node_annotation_dict

    return annotation_object

def get_annotation_object(name, node_symbols, annotation_map):
    annotation_object = {}
    annotation_object['nodeAnnotationName'] = name
    node_annotation_dict = {}
    for node_symbol in node_symbols:
        node_annotation_dict[node_symbol] = annotation_map[node_symbol]

    annotation_object['nodeAnnotation'] = node_annotation_dict

    return annotation_object

def main(sysArgs):
    logger.debug("This script retrieves the network provided by the name or uuid of the input")
    uuid = sysArgs[1]
    logger.info("Retrieving network with uuid {}".format(uuid))

    # currently only default user
    client = init_sbml4j()
    # get the output_dir
    output_dir = config['data'].get('output_dir')
    net = client.getNetwork(uuid)
    filename="{}.graphml".format(uuid)
    output_file=os.path.join(output_dir, filename)
    graphML = net.graphML()
    with open(output_file, 'w') as f:
        f.write(graphML)

if __name__ == "__main__":

    main(sys.argv)
