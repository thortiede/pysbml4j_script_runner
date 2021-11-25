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
    logger.debug("It creates a network with the counts of the symbols in all provided graphml files and downloads it to '/output'.")
    logger.info("MARKER-3A: Beginning creating networks")   
    # get the graphML files
    graphml_base_dir = config['data'].get('graphml_dir')
    graphml_subfolders = os.listdir(graphml_base_dir)
    # get the file patterns to iterate over
    file_patterns = config['data'].get('file_patterns').split(',')
    # get the output_dir
    output_dir = config['data'].get('output_dir')
    for folder in graphml_subfolders:
        logger.info("MARKER-2A: Beginning processing of folder {}".format(folder))
        sbml4j_user = folder
        client = init_sbml4j(user = sbml4j_user)
        #client.listNetworks()
        for file_pattern in file_patterns:
            logger.info("MARKER-1A: Beginning processing of file_pattern {}".format(file_pattern))
            # get the base network name from config
            base_name = config['network'].get('base_name')

            # the config option to get the annotation Information
            annotation_config = config['annotation']
            annotation_type = annotation_config.get('type_name')
            annotation_node_properties = annotation_config.get('node_properties').split(',')
            annotation_node_types = annotation_config.get('node_property_types').split(',')

            annotation_name_to_type_map = {}
            for i in range(len(annotation_node_properties)):
                annotation_name_to_type_map[annotation_node_properties[i]] = annotation_node_types[i]

            # get the base network
            net = client.getNetworkByName(base_name)
            #print(annotation_name_to_type_map)

            symbol_count = {}

            print ("-------")
            graphml_dir = os.path.join(graphml_base_dir, sbml4j_user)
            graphml_files = os.listdir(graphml_dir)
            for file in graphml_files:
                if not file.endswith('.graphml'):
                    logger.info("Skipping non-xml file {}".format(file))
                    continue
                if file_pattern not in file:
                    logger.info("Skipping xml-file {} because it does not fit the pattern {}".format(file, file_pattern))
                    continue
                #annotation_name_prefix = file.split('.')[0]
                current_file = os.path.join(graphml_dir, file)
                logger.info("MARKER0A: Beginning processing of file {}".format(current_file))
                tree = ET.parse(current_file)
                root = tree.getroot()
                key_mapping = get_key_mapping(root)
                #print("-----")
                #print(key_mapping)
                id_to_symbol_map = get_id_to_symbol_map(root, key_mapping)

                graphMLSymbols = list(id_to_symbol_map.values())
                # create the context network
                for symbol in graphMLSymbols:
                    if symbol in symbol_count:
                        symbol_count[symbol] = symbol_count.get(symbol) + 1
                    else:
                        symbol_count[symbol] = 1
                logger.info("MARKER0B: Finished processing of file {}".format(current_file))
            # end for file in graphml_files:

            logger.info("MARKER1A: Starting context creation with symbols {}".format(list(symbol_count.keys())))
            # create context
            net.createContext(list(symbol_count.keys()), networkname="context_{}_{}_{}".format(client.user, file_pattern, net.networkMappingType), minSize=0, maxSize=0)
            logger.info("MARKER1B: Finished context creation")
            # Create an annotation object for adding the DeRegNet_Node boolean property
            type_annotation_object = get_boolean_true_annotation_object("DeRegNet_Node", node_symbols=graphMLSymbols)
            #print(type_annotation_object)
            logger.info("MARKER2A: Adding boolean annotation for DeRegNet_Node")
            net.annotate(annotationDict=type_annotation_object, networkname = "DRN", doPrefixName=True)
            logger.info("MARKER2B: Finished adding boolean annotation")
            # create an annotation object for adding the number of times a node was present in a graphml
            node_annotation_object = get_annotation_object("DeRegNet_Count", symbol_count.keys(), symbol_count)
            logger.info("MARKER3A: Adding DeRegNet_Count annotation")
            net.annotate(annotationDict=node_annotation_object, networkname = file_pattern, doPrefixName=True)
            logger.info("MARKER3B: Finished adding DeRegNet_Count annotation")
            filename="{}.graphml".format(net.name)
            output_file=os.path.join(output_dir, filename)
            logger.info("MARKER4A: Writing graphml file {}".format(output_file))
            with open(output_file, 'w') as f:
                f.write(net.graphML())
                logger.info("MARKER4B: Finished writing graphml file {}".format(output_file))
            logger.info("MARKER-1B: Finished processing of file_pattern {}".format(file_pattern))
            # end for file_pattern
    
        logger.info("MARKER-2B: Finished processing of folder {}".format(folder))
        # end for folder, aka user

    logger.info("MARKER-3B: Done creating networks")   
if __name__ == "__main__":

    main(sys.argv)
