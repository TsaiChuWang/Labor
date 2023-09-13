from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls


from ryu.topology.api import get_switch, get_link, get_host,get_all_host
from ryu.lib.packet import packet, ethernet, lldp
from ryu.lib.packet import ether_types
from ryu.topology import event, switches
from ryu.lib import hub
import shutil
import sys
import heapq

class Hub(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self,*args,**kwargs):
        super(Hub,self).__init__(*args,**kwargs)
        self.topology_api_app = self
        self.discover_thread = hub.spawn(self.get_topology)

        self.switches={}
        self.links= {}
        self.ports= {}
        self.configuration={}

        self.dijkstra_array=[]

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
    def switch_features_handler(self,ev):
        # message = ev.msg # message of event
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        match = ofp_parser.OFPMatch()
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)]

        self.add_flow(datapath,0,match,actions,"default flow entry")

        self.discovery_topology()
        self.update_configuration()
        self.update_dijkstra_array()

    def add_flow(self,datapath,priority,match,actions,remind_content):
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        inst = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = ofp_parser.OFPFlowMod(datapath=datapath,priority=priority,
                                    match=match,instructions=inst);
        # print("install to datapath,"+remind_content)
        datapath.send_msg(mod);

    @set_ev_cls(ofp_event.EventOFPPacketIn,MAIN_DISPATCHER)
    def packet_in_handler(self,ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        package = packet.Packet(data=msg.data)
        package_ethernet = package.get_protocol(ethernet.ethernet)

        if package_ethernet.ethertype == ether_types.ETH_TYPE_LLDP:
            package_LLDP=package.get_protocol(lldp.lldp)
            graph=self.turn_to_graph()
            start_node = str(datapath.id)
            # try:
            #     lldp_datapathid=package_LLDP.tlvs[0].chassis_id.decode()[5:]
            #     lldp_datapathid=int(lldp_datapathid, 16)
            #     end_node = str(lldp_datapathid)
            #     print(start_node+' <---> '+end_node)
            #     shortest_path = self.find_shortest_path(graph, start_node, end_node)
            #     print("Shortest path from {} to {}: {}".format(start_node, end_node, shortest_path))
            # except ValueError:
            #     return 
            # except KeyError:
            #     return
        
        # if package_ethernet.ethertype == ether_types.
            self.print_split_line()
            for i in range(1,10):
                for j in range(1,10):
                    start_node = str(i)
                    end_node=str(j)
                    print(start_node+' <---> '+end_node)
                    shortest_path = self.find_shortest_path(graph, start_node, end_node)
                    print("Shortest path from {} to {}: {}".format(start_node, end_node, shortest_path))
            self.print_split_line(char='-',start=False)
        in_port = msg.match['in_port']
        
        match = ofp_parser.OFPMatch();
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_FLOOD)]

        self.add_flow(datapath,1,match,actions,"hub flow entry")

        out = ofp_parser.OFPPacketOut(datapath=datapath,buffer_id=msg.buffer_id,
                                            in_port=in_port,actions=actions)    

        datapath.send_msg(out);
        

    def get_topology(self):
        while(True):
            self.discovery_topology()
            self.update_configuration()
            # self.show_topology()
            self.update_dijkstra_array()
            hub.sleep(5)
    
    def discovery_topology(self):
        switch_list = get_switch(self.topology_api_app)
        for switch in switch_list:
            self.switches.update({str(switch.dp.id):switch})
    
        link_list = get_link(self.topology_api_app)
        for link in link_list:
            index=str(link.src.dpid)+"-"+str(link.dst.dpid)
            append_data={
                "source_datapath":link.src.dpid,
                "destination_datapath":link.dst.dpid,
                "port":link.src.port_no
            }
            self.links.update({index:append_data})

    def update_configuration(self):
        for link in self.links:
            link_data=self.links.get(link)
            source_datapath=str(link_data["source_datapath"])
            port=str(link_data["port"])
            destination_datapath=str(link_data["destination_datapath"])
            if source_datapath in self.configuration:
                old_data=self.configuration[source_datapath]
                old_data.update({port:destination_datapath})
                self.configuration.update({source_datapath:old_data})
            else:
                self.configuration.update({
                    source_datapath:{
                        port : destination_datapath
                    }
                })
    
    def show_topology(self):
        keys=self.configuration.keys()
        self.print_split_line('-',True)
        key_list=[int(key) for key in keys]
        key_list.sort()
        for key in key_list:
            data=self.configuration[str(key)]
            print(str(key)+" <----> "+str(data))
        self.print_split_line('-',False)

    def print_split_line(self,char='-',start=True):
        terminal_width = shutil.get_terminal_size().columns
        split_line = char * terminal_width
        if(start):
            print('\n'+split_line)
        else:
            print(split_line)
    
    def update_dijkstra_array(self):
        self.dijkstra_array=[]
        keys=self.configuration.keys()
        key_list=[int(key) for key in keys]
        key_list.sort()
        
        for key in key_list:
            append_data=[sys.maxsize for i in range(len(keys))]
            try:
                append_data[key-1]=0
                key_data=self.configuration.get(str(key))
                for port in key_data:
                    destination=key_data[port]
                    index=int(destination)-1
                    append_data[index]=1
                self.dijkstra_array.append(append_data)
            except IndexError:
                return
    
    def dijkstra(self,graph, start):
        # Create a dictionary to store the shortest distances from the start node to other nodes
        distances = {node: float('inf') for node in graph}
        distances[start] = 0

        # Priority queue to keep track of nodes to be explored
        priority_queue = [(0, start)]

        # Dictionary to store the previous node that leads to the current node
        previous_node = {node: None for node in graph}

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)

            # Ignore the node if we have already found a shorter path
            if current_distance > distances[current_node]:
                continue

            for neighbor, weight in graph[current_node].items():
                distance = current_distance + weight

                # If the new distance is shorter than the current distance, update it
                if distance < distances[neighbor]:
                    distances[neighbor] = distance
                    previous_node[neighbor] = current_node
                    heapq.heappush(priority_queue, (distance, neighbor))

        return previous_node, distances
    
    def find_shortest_path(self,graph, start, end):
        previous_node, shortest_distances = self.dijkstra(graph, start)

        # Backtrack from the end node to the start node to retrieve the path
        path = []
        current_node = end
        while current_node is not None:
            path.insert(0, current_node)
            current_node = previous_node[current_node]

        return path

    def turn_to_graph(self):
        graph={}

        for key in self.configuration.keys():
            old_key_data=self.configuration[key]
            new_key_data={}
            for inter_key in old_key_data.keys():
                value=str(old_key_data[inter_key])
                new_key_data.update({value:1})
            graph.update({key:new_key_data})
        return graph