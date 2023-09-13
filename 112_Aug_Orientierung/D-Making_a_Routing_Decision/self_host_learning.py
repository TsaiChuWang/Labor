from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls


from ryu.topology.api import get_switch, get_link, get_host,get_all_host
from ryu.lib.packet import packet, ethernet, lldp,ipv4,arp
from ryu.lib.packet import ether_types
from ryu.topology import event, switches
from ryu.lib import hub
import shutil
import sys
import heapq
import json

class Hub(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self,*args,**kwargs):
        super(Hub,self).__init__(*args,**kwargs)
        self.topology_api_app = self
        self.discover_thread = hub.spawn(self.get_topology)

        self.switches={}
        self.links= {}
        self.datapaths = {}
        self.ports= {}
        self.configuration={}
        self.switch_confguration={}

        self.switch_connected_configuration_path='./configuration/switch_connected_configuration.json'
        self.clear_switch_confguration()
        self.dijkstra_array=[]

        self.host_mac_address={}
        self.mac_to_port = {}
        self.mac_mask={}
        # self.host_mac_address={
        #     "00:04:00:00:00:01":{"1":1},
        #     "00:04:00:00:00:02":{"2":1},
        #     "00:04:00:00:00:03":{"3":1},
        #     "00:04:00:00:00:04":{"4":1}
        # }

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
    def switch_features_handler(self,ev):
        message = ev.msg # message of event
        datapath = ev.msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        match = ofp_parser.OFPMatch()
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)]
        self.add_flow(datapath,0,match,actions,"default flow entry")

        self.send_get_config_request(datapath)
        self.datapaths.update({str(datapath.id):datapath})

        self.discovery_topology()
        self.update_configuration()
        self.update_dijkstra_array()
        

    def send_get_config_request(self, datapath):
        ofp_parser = datapath.ofproto_parser

        req = ofp_parser.OFPGetConfigRequest(datapath)
        datapath.send_msg(req)

    @set_ev_cls(ofp_event.EventOFPGetConfigReply, MAIN_DISPATCHER)
    def get_config_reply_handler(self, ev):
        msg = ev.msg
        dp = msg.datapath
        ofp = dp.ofproto
        datapath=dp

        switch_datapath_configuration={
            "datapath_id":datapath.id,
            "address":datapath.address,
            "is_active":datapath.is_active,
            "flag_value":msg.flags
        } 

        flag_enum=""
        if(msg.flags==ofp.OFPC_FRAG_NORMAL):
            flag_enum="OFPC_FRAG_NORMAL"
        if (msg.flags==ofp.OFPC_FRAG_DROP):
            flag_enum="OFPC_FRAG_DROP"
        if (msg.flags==ofp.OFPC_FRAG_REASM):
            flag_enum="OFPC_FRAG_REASM"
        if (msg.flags==ofp.OFPC_FRAG_MASK):
            flag_enum="OFPC_FRAG_MASK"
        switch_datapath_configuration.update({"flag_enum":flag_enum})
        switch_datapath_configuration.update({"miss_send_len":msg.miss_send_len})
        self.switch_confguration.update({str(datapath.id):switch_datapath_configuration})
        self.write_switch_confguration()
    
    def write_switch_confguration(self):
        self.clear_switch_confguration()
        with open(self.switch_connected_configuration_path, 'w') as json_file:
            json.dump(self.switch_confguration, json_file)
            json_file.close()
    
    def clear_switch_confguration(self):
        with open(self.switch_connected_configuration_path, 'w') as json_file:
            json.dump({}, json_file)
            json_file.close()

    def add_flow(self,datapath,priority,match,actions,remind_content):
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        inst = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS,
                                             actions)]

        mod = ofp_parser.OFPFlowMod(datapath=datapath,priority=priority,
                                    match=match,instructions=inst);
        # print("install to datapath,"+remind_content)
        datapath.send_msg(mod);

    #對交換器的Flow Entry取得資料
    @set_ev_cls(ofp_event.EventOFPPortStatsReply, MAIN_DISPATCHER)
    def port_stats_reply_handler(self, ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
        in_port = msg.match['in_port']
        print("switch_status")
        print(datapath.id)
        print(in_port)
        self.print_split_line()

    @set_ev_cls(ofp_event.EventOFPPacketIn,MAIN_DISPATCHER)
    def packet_in_handler(self,ev):
        msg = ev.msg
        datapath = msg.datapath
        ofproto = datapath.ofproto
        ofp_parser = datapath.ofproto_parser

        package = packet.Packet(data=msg.data)
        package_ethernet = package.get_protocol(ethernet.ethernet)

        in_port = msg.match['in_port']

         # avoid broadcasts from LLDP 
        if package_ethernet.ethertype == ether_types.ETH_TYPE_LLDP or package_ethernet.ethertype == ether_types.ETH_TYPE_IPV6:
            return

        if(package_ethernet.ethertype==2054):
            dst = package_ethernet.dst
            src = package_ethernet.src
            dpid = datapath.id

            # print(package)
            
            if(src not in self.host_mac_address):
                try:
                    self.host_mac_address.update({src:{str(datapath.id):str(in_port)}})
                    print(self.host_mac_address)
                    match = ofp_parser.OFPMatch(eth_dst=src)
                    actions = [ofp_parser.OFPActionOutput(in_port)]
                    insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                    mod = ofp_parser.OFPFlowMod(
                            datapath=datapath,
                            match=match,
                            cookie=0,
                            command=ofproto.OFPFC_ADD,
                            idle_timeout=0,
                            hard_timeout=0,
                            priority=3,
                            instructions=insturctions
                        )
                    datapath.send_msg(mod)
                except KeyError:
                    return
            else:
                try:
                    graph=self.turn_to_graph()
                    start_node=str(datapath.id)
                    end_node = str(list(self.host_mac_address[src].keys())[0])
                    shortest_path = self.find_shortest_path(graph, start_node, end_node)
                    match = ofp_parser.OFPMatch(eth_dst=src)

                    if(len(shortest_path)==1):

                        actions = [ofp_parser.OFPActionOutput(in_port)]
                        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                        mod = ofp_parser.OFPFlowMod(
                                datapath=datapath,
                                match=match,
                                cookie=0,
                                command=ofproto.OFPFC_ADD,
                                idle_timeout=0,
                                hard_timeout=0,
                                priority=3,
                                instructions=insturctions
                            )
                        datapath.send_msg(mod)
                    
                    elif(len(shortest_path)==2):

                        next_node=shortest_path[1]
                        output_port=self.get_outport_by_datapath_id(start_node,next_node)
                        actions = [ofp_parser.OFPActionOutput(output_port)]
                        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                        mod = ofp_parser.OFPFlowMod(
                                datapath=datapath,
                                match=match,
                                cookie=0,
                                command=ofproto.OFPFC_ADD,
                                idle_timeout=0,
                                hard_timeout=0,
                                priority=3,
                                instructions=insturctions
                            )
                        datapath.send_msg(mod)

                    else:
                        next_node=shortest_path[1]
                        output_port=self.get_outport_by_datapath_id(start_node,next_node)
                        # print("shortpath= "+str(shortest_path)+", this= "+str(datapath.id)+": port= "+str(output_port)+", next= "+str(next_node))
                        actions = [ofp_parser.OFPActionOutput(output_port)]
                        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                        mod = ofp_parser.OFPFlowMod(
                                datapath=datapath,
                                match=match,
                                cookie=0,
                                command=ofproto.OFPFC_ADD,
                                idle_timeout=0,
                                hard_timeout=0,
                                priority=3,
                                instructions=insturctions
                            )
                        datapath.send_msg(mod)

                except KeyError:
                    return

            arp_pkt = package.get_protocol(arp.arp)
            print(arp_pkt.to_jsondict()['arp']['opcode'])

            # print(dst)
            # print(dst == "ff:ff:ff:ff:ff:ff")
            if(dst == "ff:ff:ff:ff:ff:ff"):
                # print("datapath= "+str(datapath.id)," ,ingresport= "+str(in_port))
                match = ofp_parser.OFPMatch()
                actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_FLOOD)]
                insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = ofp_parser.OFPFlowMod(
                    datapath=datapath,
                    match=match,
                    cookie=0,
                    command=ofproto.OFPFC_ADD,
                    idle_timeout=0,
                    hard_timeout=0,
                    priority=1,
                    instructions=insturctions
                )
                datapath.send_msg(mod)
            else:
                print(datapath.id)
                print(src)
                print(dst)
                print(in_port)
                self.print_split_line()

            data = msg.data
            out = ofp_parser.OFPPacketOut(
                datapath=datapath,
                buffer_id=msg.buffer_id,
                in_port=in_port,
                actions=actions,
                data=data
            )
            datapath.send_msg(out)
                
    def add_flow_by_shortest_path(self,shortest_path,datapath,ofp_parser,src,dst,ofproto):
        next_node=shortest_path[1]
        # print("next-node= "+str(next_node))
        # print(self.configuration)
        # print(self.configuration[str(datapath.id)])
        for node in range(len(shortest_path)-1):
            out_port=self.get_outport_by_datapath_id(shortest_path[node],shortest_path[node+1])
            print(shortest_path[node]+" --> "+shortest_path[node+1]+" :"+str(out_port))

            if(out_port != 0):
                datapath=self.datapaths[shortest_path[node]]
                # print(datapath)
                match = ofp_parser.OFPMatch(
                    eth_type= ether_types.ETH_TYPE_ARP,
                    eth_src=src,
                    eth_dst=dst
                )
                actions = [ofp_parser.OFPActionOutput(out_port)]
                insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)]
                mod = ofp_parser.OFPFlowMod(
                    datapath=datapath,
                    match=match,
                    cookie=0,
                    command=ofproto.OFPFC_ADD,
                    idle_timeout=0,
                    hard_timeout=0,
                    priority=3,
                    instructions=insturctions
                )

                # Send the flow mod message to the switch
                datapath.send_msg(mod)
                print("ada")


    
    def get_outport_by_datapath_id(self,datapath_id,next_node):
        out_port=0
        for port in self.configuration[str(datapath_id)].keys():
            mapped_switch_port=self.configuration[str(datapath_id)][port]
            if(mapped_switch_port==str(next_node)):
                out_port=int(port)
        return out_port

    def find_link_node(self,mac_address):
        print("mac_address= "+str(mac_address))
        print(self.configuration)
        index=self.host_mac_address.index(mac_address)*(-1)
        for datapath_id in self.configuration.keys():
            ports=self.configuration[datapath_id]
            for port in ports.keys():
                if(str(index)==ports[port]):
                    print("datapath_id= "+str(datapath_id))
                    print("port= "+str(port))
                    return (datapath_id,port)

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
        print(self.configuration)

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
