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
    logger.debug("This script reads in the graphml files found in the folder '/graphml'.")
    logger.debug("It creates a network for each of the graphml files found and downloads it to '/output'.")

    client = init_sbml4j(user = config['server'].get('user'))
    #client.listNetworks()

    # get the base network name from config
    base_name = config['network'].get('base_name')
    # get the graphML files
    graphml_dir = config['data'].get('graphml_dir')
    # get the output_dir
    output_dir = config['data'].get('output_dir')
    # the config option to get the annotation Information
    annotation_config = config['annotation']
    annotation_type = annotation_config.get('type_name')
    annotation_node_properties = annotation_config.get('node_properties').split(',')
    annotation_node_types = annotation_config.get('node_property_types').split(',')

    annotation_name_to_type_map = {}
    for i in range(len(annotation_node_properties)):
        annotation_name_to_type_map[annotation_node_properties[i]] = annotation_node_types[i]
    #print(annotation_name_to_type_map)
    print ("-------")
    graphml_files = os.listdir(graphml_dir)
    for file in graphml_files:
        try:
            annotation_name_prefix = file.split('.')[0]
            current_file = os.path.join(graphml_dir, file)
            logger.debug("Processing File {}".format(current_file))
            tree = ET.parse(current_file)
            root = tree.getroot()
            key_mapping = get_key_mapping(root)
            #print("-----")
            #print(key_mapping)
            id_to_symbol_map = get_id_to_symbol_map(root, key_mapping)

            # get the base network
            net = client.getNetworkByName(base_name)
            graphMLSymbols = list(id_to_symbol_map.values())
            # create the context network
            net.createContext(graphMLSymbols, networkname="{}_{}".format(annotation_name_prefix, net.networkMappingType), minSize=0, maxSize=0)

            # add the deregnetNode annotation
            type_annotation_object = get_boolean_true_annotation_object("{}_{}".format(annotation_name_prefix, annotation_type), node_symbols=graphMLSymbols)
            print(type_annotation_object)
            net.annotate(annotationDict=type_annotation_object, networkname = annotation_type, doPrefixName=True)

            # iterate over the nodes, gahter all attributes
            node_id_to_annotation_map = {}
            for graph in root.iter('{http://graphml.graphdrawing.org/xmlns}graph'):
                for child in graph.iter('{http://graphml.graphdrawing.org/xmlns}node'):
                    node_id_to_annotation_map[child.attrib['id']] = get_node_data_elements(child, key_mapping, annotation_name_to_type_map)
            #print(node_id_to_annotation_map)

            # for each of the desired/configured annotations, create an annotation object
            for node_annotation in annotation_node_properties:

                # need a map, linking the node symbol to the actual annotation element for this node_annotation
                symbol_to_annotation_map = {}
                for node_id, node_annotation_map in node_id_to_annotation_map.items():
                    symbol_to_annotation_map[node_annotation_map['symbol']] = node_annotation_map[node_annotation]
                #print(symbol_to_annotation_map)
                node_annotation_object = get_annotation_object("{}_{}".format(annotation_name_prefix, node_annotation), node_symbols=graphMLSymbols, annotation_map=symbol_to_annotation_map)
                net.annotate(annotationDict=node_annotation_object, networkname = node_annotation, doPrefixName=True)

            filename="{}.graphml".format(net.name)
            output_file=os.path.join(output_dir, filename)

            with open(output_file, 'w') as f:
                f.write(net.graphML())
        except:
            logger.warning("Unable to create a network and/or graphml for input {}".format(file))


if __name__ == "__main__":

    main(sys.argv)
