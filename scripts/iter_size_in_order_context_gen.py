# This is the benchmarking script that generates context networks with random genes
# This version iterates 'iter' times and creates contexts for 1, 2, 3, ..., size number of randomly drawn symbols
# The size value is used in order, so for each iteration, first size 1 is used, then size 2, and so on
# This might influence performance, if the node-list of the size 10 network is similar to the size 9 network that was generated right before it
# SBML4j can reuse parts of the database results then.
# It might be necessary to also evaluate the database query times, and in general times on the server side, not only client
# The timing data is put in the graphml files that are generated

import os
import sys

from pysbml4j import Sbml4j
from pysbml4j import Configuration

import logging
from logging.config import fileConfig
import configparser

import xml.etree.ElementTree as ET

from codetiming import Timer

from random import seed
from random import randint
from random import choices


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

def draw_elements(all_elements, number_to_draw):
    returnList = []
    for i in range(number_to_draw):
        list_index = randint(0, len(all_elements)-1) 
        returnList.append(all_elements[list_index])
    return returnList

def main(sysArgs):
    logger.debug("This script generates contexts for random sets of gene-symbols of the base network provided in the config file")
    client = init_sbml4j(user = "contextcreationtimer")
    # get the output_dir
    output_dir = config['data'].get('output_dir')
    # intialize the random number generator
    seed(config['random'].get('seed'))
    # get the base network name from config
    base_name = config['network'].get('base_name')
    
    # get the number of iterations
    num_iter = config.getint('loop', 'iter')
    # get the max number of symbols
    max_symbol_count = config.getint('loop', 'size')
    for iteration in range(1,num_iter+1):
        for context_size in range(1, max_symbol_count+1):
            # get the base network
            net = client.getNetworkByName(base_name)
            # get all symbols
            network_nodeSymbols = net.getOptions()['filter']['nodeSymbols']
            context_symbols = draw_elements(network_nodeSymbols, context_size)

            # create context
            contextMinSize=0
            contextMaxSize=2
            # initialize the timer
            t = Timer("context_timer_{}_{}".format(context_size, iteration))
            t.start()
            # calculate the actual context
            try:
                name_of_network = "size-{}-iter-{}_{}_{}-{}".format(context_size, iteration, context_symbols, contextMinSize, contextMaxSize)
                net.createContext(context_symbols, networkname=name_of_network, minSize=contextMinSize, maxSize=contextMaxSize)
                elapsed_time = t.stop()
                logger.info("Created network context for {} with timer {} which took {} seconds".format(context_symbols, t, elapsed_time))
                filename="size-{}-iter-{}-time-{:0.4f}-{}.graphml".format(context_size, iteration, elapsed_time, net.name)
                output_file=os.path.join(output_dir, filename)
                with open(output_file, 'w') as f:
                    f.write(net.graphML())
            except:
                logger.info("Skipping context for {}, as it could not be generated".format(name_of_network))

if __name__ == "__main__":

    main(sys.argv)
