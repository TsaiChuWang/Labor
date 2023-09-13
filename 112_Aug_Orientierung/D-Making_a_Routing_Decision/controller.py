from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls

import shutil
from ryu.lib import hub
import time
from ryu.lib.packet import ether_types
from ryu.lib.packet import packet, ethernet, lldp
import heapq

class Topology_Discovery_by_LLDP_update_five_seconds(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # 確定控制器所用OpenFlow版本

    # 交換機啟動得初始化函數
    def __init__(self, *args, **kwargs):
        super(Topology_Discovery_by_LLDP_update_five_seconds, self).__init__(*args, **kwargs)
        self.discover_thread = hub.spawn(self.every_five_second_monitoring)     # 建立一個 thread 用於每 5 秒的監控

        self.start_time = time.time()   # 紀錄啟動時間

        self.datapaths = {} # 儲存整個網路的 Datapath 物件

        self.ports_details = {}   # 整個網路的交換機的 port 統計資訊
        self.switch_ports = {}  # 連接交換機與 port 的對應關係
        self.switch_graph ={}   # 連接交換機的 edge with weight

        self.host_may_existed = {} # 主機可能存在的位置
        self.host_mac_learning = {}

        self.ports_statistic = {}   # 整個網路的交換機的 port 統計資訊

        self.priority = 10

    # 控制器事件響應 switch_features_handler 響應 OFPT_FEATURES_REPLY
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_features_handler(self, event):
        # 取得資料 
        message = event.msg     # 事件的訊息
        datapath = message.datapath   # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        # 設定 table-miss flow entry : 
        match = ofp_parser.OFPMatch()   # 匹配所有封包
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]   # 將整個封包發送到控制器
        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
        flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message , 屬於Controller-to-switch Messages
            datapath = datapath,    # 交換機
            match = match,  # 匹配項目
            cookie = 0, # Cookie 為 0
            command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
            idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
            hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
            priority = 0,   # 優先級為 0 （ table-miss 的必要條件）
            instructions = insturctions # 執行的動作
        )
        datapath.send_msg(flow_add_modification_message)    # 發送往交換機
        # self.logger.info("Datapath {0} add table-miss flow entry with actions: send entire package to controller.".format(datapath.id))    # 顯示添加完成的 log

        self.datapaths.update({datapath.id : datapath}) # 初始化交換機物件
        self.switch_ports.update({datapath.id : {}})    # 初始化交換機與 port 的對應關係
        self.switch_graph.update({datapath.id : {}})    # 初始化交換機的 edge with weight
        self.ports_details.update({datapath.id : {}})
        
        match = ofp_parser.OFPMatch(eth_type = 34525)   # 匹配所有封包 
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]   # 將整個封包發送到控制器
        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
        flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message , 屬於Controller-to-switch Messages
            datapath = datapath,    # 交換機
            match = match,  # 匹配項目
            cookie = 0, # Cookie 為 0
            command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
            idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
            hard_timeout = 0,   # 4 秒後過期
            priority = 1,   # 優先級為 1
            instructions = insturctions # 執行的動作
        )
        datapath.send_msg(flow_add_modification_message)    # 發送往交換機
        # self.logger.info("Datapath {:2d} add flow entry matched LLDP package with actions: send entire package to controller.".format(datapath.id))    # 顯示添加完成的 log

        self.send_port_desc_stats_request(datapath) # 發送一個 send_port_desc_stats_request 給各個switch
        # self.logger.info("Datapath {:2d} send an OFPMP_PORT_STATS Request.".format(datapath.id))    # 顯示添加完成的 log
        self.show_topology_lldp()   # 顯示拓樸 （LLDP）

        
        # datapath.send_msg(flow_add_modification_message)    # 發送往交換機
        # match = ofp_parser.OFPMatch(ipv4_src = "10.0.0.10")   
        # actions = [ofp_parser.OFPActionOutput(port = 2)]
        # self.add_flow_entry(match, actions, 10, datapath, message)   # 優先級為

    # OFPPortDescStatsRequest 的響應，統計 port 的資訊
    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, event):
        # 取得訊息
        datapath = event.msg.datapath    # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
        
        ports = {}  # 交換機上的 port

        # 遍歷 event 中收到的每個 port 的統計訊息
        for statistic in event.msg.body:
            if statistic.port_no <= ofproto.OFPP_MAX:    # 如果 port_no(port number) 小於或等於 OFPP_MAX（最大的 port number ) -> 表示該 port 有效且不是 reserved port
                ports.update( {statistic.port_no : statistic.hw_addr} )   # 添加有效的 port 訊息  port number : MAC 地址
        self.ports_details.update({ datapath.id : ports} )    # 更新該交換機的 port 統計資訊

        ports_string = ""
        for key in self.ports_details[datapath.id].keys():
            ports_string += " {} : {:2s}, ".format(key, self.ports_details[datapath.id][key])
        # self.logger.info("Switch{:2d} with ports infromation : {}".format(datapath.id, ports_string))

        # 遍歷 ports 的每個 port, 並且為該 port 發送 LLDP 封包
        for port_number in ports.keys():
            ingress_port = int(port_number)   # 輸入 port 為 port 的 port number
            match = ofp_parser.OFPMatch(eth_type = 34525 , in_port = ingress_port) # 如果封包匹配 in_port = ingress_port 且 為 LLDP 類型

            for other_port_number in ports.keys():    # 遍歷其他非 ingress_port 的 port
                if(other_port_number != ingress_port):    # 如果是其他 port
                    out_port = other_port_number    # 轉發 port 為 other_port
                    self.send_lldp_packet(datapath, other_port_number, ports[other_port_number], 1)  # 發送 LLDP 封包

                    actions = [ofp_parser.OFPActionOutput(out_port), 
                               ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]    # 進行轉發封包的 action : 轉發到 output_port 以及控制器
                    insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
                    flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message , 屬於Controller-to-switch Messages
                        datapath = datapath,    # 交換機
                        match = match,  # 匹配項目
                        cookie = 0, # Cookie 為 0
                        command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
                        idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
                        hard_timeout = 4,   # 不限制硬性過期時間 （永久存在）
                        priority = 2,   # 優先級為 2，為了覆蓋掉預設的 LLDP 封包轉發動作
                        instructions = insturctions # 執行的動作
                    )
                    datapath.send_msg(flow_add_modification_message)    # 發送往交換機
                    # self.logger.info("Switch{:2d} add a flow entry with match field : eth_type = 34525 , in_port = {}".format(datapath.id, ingress_port))
        ports = {}
        # 遍歷 event 中收到的每個 port 的統計訊息
        for statistic in event.msg.body:
            if statistic.port_no <= ofproto.OFPP_MAX:    # 如果 port_no(port number) 小於或等於 OFPP_MAX（最大的 port number ) -> 表示該 port 有效且不是 reserved port

                curr_speed =statistic.curr_speed
                max_speed = statistic.max_speed

                update_data = {
                    statistic.port_no : {
                        "hw_addr" : statistic.hw_addr,
                        "name" : statistic.name.decode(),
                        "max_speed" : max_speed,
                        "curr_speed" : curr_speed
                    }
                }
                if(datapath.id in self.ports_statistic.keys() and statistic.port_no in self.ports_statistic[datapath.id].keys()):
                    if('rx_bytes' in self.ports_statistic[datapath.id][statistic.port_no].keys()):
                            elapsed_time = self.ports_statistic[datapath.id][statistic.port_no]['update_time']
                            rx_packets = self.ports_statistic[datapath.id][statistic.port_no]['rx_packets']
                            tx_packets = self.ports_statistic[datapath.id][statistic.port_no]['tx_packets']
                            rx_bytes = self.ports_statistic[datapath.id][statistic.port_no]['rx_bytes']
                            tx_bytes = self.ports_statistic[datapath.id][statistic.port_no]['tx_bytes']
                            rx_errors = self.ports_statistic[datapath.id][statistic.port_no]['rx_errors']
                            tx_errors = self.ports_statistic[datapath.id][statistic.port_no]['tx_errors']
                                
                            update_data[statistic.port_no].update({'update_time' : elapsed_time})
                            update_data[statistic.port_no].update({'rx_packets' : rx_packets})
                            update_data[statistic.port_no].update({'tx_packets' : tx_packets})
                            update_data[statistic.port_no].update({'rx_bytes' : rx_bytes})
                            update_data[statistic.port_no].update({'tx_bytes' : tx_bytes})
                            update_data[statistic.port_no].update({'rx_errors' : rx_errors})
                            update_data[statistic.port_no].update({'tx_errors' : tx_errors})

                    if('free_bandwidth_rx' in self.ports_statistic[datapath.id][statistic.port_no].keys()):
                        free_bandwidth_rx = self.ports_statistic[datapath.id][statistic.port_no]['free_bandwidth_rx']
                        free_bandwidth_tx = self.ports_statistic[datapath.id][statistic.port_no]['free_bandwidth_tx']

                        update_data[statistic.port_no].update({'free_bandwidth_rx' : free_bandwidth_rx})
                        update_data[statistic.port_no].update({'free_bandwidth_tx' : free_bandwidth_tx})

                        occupied_bandwidth_rx = self.ports_statistic[datapath.id][statistic.port_no]['occupied_bandwidth_rx']
                        occupied_bandwidth_tx = self.ports_statistic[datapath.id][statistic.port_no]['occupied_bandwidth_tx']

                        update_data[statistic.port_no].update({'occupied_bandwidth_rx' : occupied_bandwidth_rx})
                        update_data[statistic.port_no].update({'occupied_bandwidth_tx' : occupied_bandwidth_tx})
                 
                ports.update(update_data)   # 添加有效的 port 訊息  port number : MAC 地址
        self.ports_statistic.update({ datapath.id : ports} )    # 更新該交換機的 port 統計資訊

    # 響應封包進入控制器的事件
    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, event):
        message = event.msg # message of event
        datapath = event.msg.datapath    # 數據平面的交換機（datapath）結構

        package = packet.Packet(data = message.data)  # 取得封包
        datapath_id = datapath.id   # 來源的交換機
        ingress_port  = message.match['in_port']    # 輸入的 port

        package_ethernet = package.get_protocol(ethernet.ethernet)  # ethernet frame

        # 過濾協議為 LLDP 的封包
        if(package_ethernet.ethertype == ether_types.ETH_TYPE_LLDP):
            package_LLDP = package.get_protocol(lldp.lldp)    # 取得 LLDP 封包
            lldp_datapathid = package_LLDP.tlvs[0].chassis_id.decode()  # 連接到的目標交換機 ID
            lldp_ingress_port = package_LLDP.tlvs[1].port_id.decode()   # 連接到的目標交換機 port
            
            origin_graph = self.switch_graph[datapath_id]   # 未更新的圖[本交換機]
            try:
                origin_graph.update({lldp_datapathid : self.ports_statistic[datapath_id][ingress_port]['free_bandwidth_tx']})
            except KeyError:
                try:
                    origin_graph.update({lldp_datapathid : self.ports_statistic[datapath_id][ingress_port]['curr_speed']})
                except KeyError:
                    origin_graph.update({lldp_datapathid : 10000000})
            self.switch_graph.update({datapath_id : origin_graph})  # 更新圖到全圖 

            origin_switch_port = self.switch_ports[datapath_id] # 未更新的交換機與 port 的連接關係[本交換機]
            origin_switch_port.update({ingress_port : lldp_datapathid}) # 更新交換機與 port 的連接關係[本交換機]，port_number : connected_switch  
            self.switch_ports.update({datapath_id : origin_switch_port})    # 更新交換機與 port 的連接關係[整個拓樸]
        
            # 這個解註解會打印出交換機相連的邊以及 port
            # print("switch{:2d} : {} <---> switch{:2s} : {}".format(datapath_id, ingress_port, lldp_datapathid, lldp_ingress_port))   
        
        if(package_ethernet.ethertype == 2054):
            # self.logger.info("from switch{:2d} and port{:2d}".format(datapath_id,ingress_port))
            # self.init_flow_entry(datapath)

            source_mac = package_ethernet.to_jsondict()['ethernet']['src']
            destination_mac = package_ethernet.to_jsondict()['ethernet']['dst']

            if(source_mac not in self.host_mac_learning):
                # self.logger.info("Mac address {} has learned ,connected with switch{:2d}".format(source_mac,datapath_id))
                self.host_mac_learning.update({source_mac : [datapath_id , ingress_port]})

            if(destination_mac == 'ff:ff:ff:ff:ff:ff'):
                self.logger.info("Destination address hasn't learned ,add flooding with dijastra")
                # self.add_flooding_flow_entry(source_mac)
                self.destination_does_not_valid(datapath,ingress_port,source_mac)
            else:
                self.logger.info("Add flow entry with match source mac address : {} and destination mac address : {} ".format(source_mac,destination_mac))
                self.logger.info(self.host_mac_learning)
                self.destination_does_valid(source_mac,destination_mac)

    # 取得 port 的統計資訊
    @set_ev_cls(ofp_event.EventOFPPortStatsReply,MAIN_DISPATCHER)
    def _port_stats_reply_handler(self,event):
        ofproto = event.msg.datapath.ofproto
        ports = event.msg.body

        for port in ports:
            port_number = port.port_no
            datapath_id = event.msg.datapath.id
            if(port_number < ofproto.OFPP_MAX):
                rx_packets = port.rx_packets
                tx_packets = port.tx_packets
                rx_bytes = port.rx_bytes
                tx_bytes = port.tx_bytes
                rx_errors = port.rx_errors
                tx_errors = port.tx_errors

                if('rx_bytes' in self.ports_statistic[datapath_id][port_number].keys()):
                    now_time = time.time()  # 取得現在時間
                    elapsed_time = now_time - self.start_time   # 取得執行時間
                    last_time = float(self.ports_statistic[datapath_id][port_number]['update_time'])
                    interval_time = elapsed_time - last_time
                    
                    rx_bytes_diff = rx_bytes - self.ports_statistic[datapath_id][port_number]['rx_bytes']
                    tx_bytes_diff = tx_bytes - self.ports_statistic[datapath_id][port_number]['tx_bytes']

                    port_statistic = self.ports_statistic[datapath_id][port_number]

                    occupied_bandwidth_rx = (rx_bytes_diff / interval_time) * 8
                    occupied_bandwidth_tx = (tx_bytes_diff / interval_time) * 8
                    
                    self.ports_statistic[datapath_id][port_number].update({'occupied_bandwidth_rx' : occupied_bandwidth_rx})
                    self.ports_statistic[datapath_id][port_number].update({'occupied_bandwidth_tx' : occupied_bandwidth_tx})

                    free_bandwidth_rx = abs(port_statistic['curr_speed'] - occupied_bandwidth_rx)
                    free_bandwidth_tx = abs(port_statistic['curr_speed'] - occupied_bandwidth_tx)

                    self.ports_statistic[datapath_id][port_number].update({'free_bandwidth_rx' : free_bandwidth_rx})
                    self.ports_statistic[datapath_id][port_number].update({'free_bandwidth_tx' : free_bandwidth_tx})
                    
                    if(port.port_no in self.switch_ports[datapath_id].keys()):
                        self.switch_graph[datapath_id].update({self.switch_ports[datapath_id][port.port_no] : free_bandwidth_tx})   # 更新圖為當前可用的 bandwidth
                else:
                    now_time = time.time()  # 取得現在時間
                    elapsed_time = now_time - self.start_time   # 取得執行時間
                    self.ports_statistic[datapath_id][port_number].update({'update_time' : elapsed_time})
                    self.ports_statistic[datapath_id][port_number].update({'rx_packets' : rx_packets})
                    self.ports_statistic[datapath_id][port_number].update({'tx_packets' : tx_packets})
                    self.ports_statistic[datapath_id][port_number].update({'rx_bytes' : rx_bytes})
                    self.ports_statistic[datapath_id][port_number].update({'tx_bytes' : tx_bytes})
                    self.ports_statistic[datapath_id][port_number].update({'rx_errors' : rx_errors})
                    self.ports_statistic[datapath_id][port_number].update({'tx_errors' : tx_errors})
                    if(port.port_no in self.switch_ports[datapath_id].keys()):
                        self.switch_graph[datapath_id].update({self.switch_ports[datapath_id][port.port_no] : 10000000})    # 更新圖，預設為可用 bandwidth

        if(len(self.host_mac_learning.keys())>0):
            self.print_split_line("=",True)
            self.logger.info("Inspire EventOFPPortStatsReply: Datapath{:2d}".format(event.msg.datapath.id))
            self.logger.info(self.switch_graph[event.msg.datapath.id])
            # self.equivalent()
            self.equivalent_datapath(event.msg.datapath.id)
            self.print_split_line("=",False)

    def equivalent(self):
        for mac in self.host_mac_learning.keys():
            datapath_id = self.host_mac_learning[mac][0]
            port_number = self.host_mac_learning[mac][1]

            graph = self.transform_graph()
            
            for source_datapath in self.datapaths.keys():
                if(int(datapath_id)!= int(source_datapath)):
                    path  = self.find_shortest_path_dijkstra(source_datapath,datapath_id,graph)
                    next_node = path[1]
                    output = self.find_connected_port(source_datapath,next_node)
                    self.logger.info("Datapath{:2d} to datapath{:2d} : {}, next = {:2d}, port = {:2d}".format(source_datapath,datapath_id,str(path),int(next_node),int(output)))
                    
                    self.add_path_flow_entry(mac,path,port_number)

        self.priority = self.priority +1

    def equivalent_datapath(self,source_datapath_id):
        for mac in self.host_mac_learning.keys():
            datapath_id = self.host_mac_learning[mac][0]
            port_number = self.host_mac_learning[mac][1]

            graph = self.transform_graph()
            
            for source_datapath in self.datapaths.keys():
                if(int(datapath_id)!= int(source_datapath)):
                    path  = self.find_shortest_path_dijkstra(source_datapath,datapath_id,graph)
                    next_node = path[1]
                    output = self.find_connected_port(source_datapath,next_node)
                    if(str(source_datapath_id) == str(source_datapath)):
                        self.logger.info("Datapath{:2d} to datapath{:2d} : {}, next = {:2d}, port = {:2d}".format(source_datapath,datapath_id,str(path),int(next_node),int(output)))
                    
                    self.add_path_flow_entry(mac,path,port_number)

            
            
    def add_path_flow_entry(self,dst_mac,path,out_put_port):
        for index,node in enumerate(path[:-1]):
            start = int(node)
            end = int(path[index+1])
            port = self.find_connected_port(start,end)

            datapath = self.datapaths[start]
            ofp_parser = datapath.ofproto_parser

            message = "Datapath {:2d} add flow entry with match : eth_src = {} , actions : forwarding to port{:2d}"
            match = ofp_parser.OFPMatch(eth_dst = dst_mac)   # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address]為匹配項目
            actions = [ofp_parser.OFPActionOutput(port = port)]
            self.add_flow_entry(match, actions, self.priority, datapath, message)   

        datapath = self.datapaths[int(path[-1])]
        ofp_parser = datapath.ofproto_parser

        message = "Datapath {:2d} add flow entry with match : eth_src = {} , actions : forwarding to port{:2d}"
        match = ofp_parser.OFPMatch(eth_dst = dst_mac)   # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address]為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = out_put_port)]
        self.add_flow_entry(match, actions, self.priority, datapath, message)   # 優先級為

    # def 

    def send_port_status_request(self, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
        
        # 取得 switch port 的 mac address
        request = ofp_parser.OFPPortStatsRequest(datapath, 0)   # 請求有關交換機 port 的詳細訊息
        datapath.send_msg(request)  # 發送一條 OFPPortDescStatsRequest ，透過 OFPPortDescStatsReply 取得 port 資訊

    # 取得 port 的資訊
    def send_port_desc_stats_request(self, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
    
        # 取得 switch port 的 mac address
        request = ofp_parser.OFPPortDescStatsRequest(datapath, 0)   # 請求有關交換機 port 的詳細訊息
        datapath.send_msg(request)  # 發送一條 OFPPortDescStatsRequest ，透過 OFPPortDescStatsReply 取得 port 資訊

    # 發送 LLDP 封包
    def send_lldp_packet(self, datapath, port, hardware_address, ttl):
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        # 產生一個封包 object
        lldp_package = packet.Packet()

        # 添加 ethernet header
        lldp_package.add_protocol(
            ethernet.ethernet(
                ethertype = ether_types.ETH_TYPE_LLDP, # ethertype: LLDP
                src = hardware_address , # src: 發送 LLDP 封包的 switch port 的 mac 地址
                dst = lldp.LLDP_MAC_NEAREST_BRIDGE # dst: LLDP_MAC_NEAREST_BRIDGE 連接交換機最近的 mac
            )
        )

        chassis_id = lldp.ChassisID(subtype=lldp.ChassisID.SUB_LOCALLY_ASSIGNED, chassis_id=str(datapath.id))   # chassis_id: 發送 LLDP 封包的 switch id
        port_id = lldp.PortID(subtype=lldp.PortID.SUB_LOCALLY_ASSIGNED, port_id=str(port))  # port_id: 發送 LLDP 封包的 switch port id

        chassis_id.chassis_id = chassis_id.chassis_id.encode()    # 必須轉換成 byte 不然會在 serialize 出錯
        port_id.port_id = port_id.port_id.encode()
        
        # 添加 LLDP TLV（ Type / Length / Value )
        ttl = lldp.TTL(ttl=ttl) # 存活時間
        end = lldp.End()    
        tlvs = (chassis_id, port_id, ttl, end) # tlvs = 設備 ID, port ID , time-to-live , end
        lldp_package.add_protocol(lldp.lldp(tlvs))  # 加入 LLDP header
        lldp_package.hop_limit=ttl  # 設定跳數限制   
        
        lldp_package.serialize() # 序列化 LLDP 封包

        data = lldp_package.data # 將 data 指定為封包的二進位制值
        actions = [ofp_parser.OFPActionOutput(port=port)] # Action 指定為將封包轉發到指定 port

        # 創建一條 OFPPacketOut message 將封包發送到交換機
        out = ofp_parser.OFPPacketOut(
            datapath = datapath,    # 交換機 
            buffer_id = ofproto.OFP_NO_BUFFER,  # 將整個封包傳送出去
            in_port = ofproto.OFPP_CONTROLLER,  # 指定從控制器傳入
            actions = actions,  # 將封包轉發到指定 port
            data = data     # 封包資料
        )
        datapath.send_msg(out) # 將封包發送到交換機
        # self.logger.info("Switch{:2d} send a LLDP packet with chassis_id = {:2s}, port_id = {:2s}, mac address = {} ttl = {}".format(datapath.id, chassis_id.chassis_id.decode(), port_id.port_id.decode(), hardware_address, ttl))

    # 打印出跟 terminal 同長度的分割線
    def print_split_line(self, char = '-', start = True):
        terminal_width = shutil.get_terminal_size().columns # 取得 terminal 長度
        split_line = char * terminal_width  # 分割線
        if(start):  # 起始分割線
            self.logger.info('\n'+split_line)
        else:   # 結束分割線
            self.logger.info(split_line)

    # 顯示拓樸 (topology lldp)
    def show_topology_lldp(self):
        self.print_split_line('=', True)    # 起始分割線
        now_time = time.time()  # 取得現在時間
        elapsed_time = now_time - self.start_time   # 取得執行時間

        self.logger.info("Topology of network with elapsed time: {:.6f}".format(elapsed_time))  # 顯示執行時間
        switch_list_string = "" 
        for id in self.datapaths.keys():   # 遍歷交換機
            switch_list_string += " {:2d}, ".format(id) # 將交換機資訊加入訊息
        self.logger.info("Switch list :"+switch_list_string[:-2])   # 打印出訊息
        
        switch_in_edges = set() # 統計已連接的交換機數量
        for datapath_id in self.switch_graph.keys():    # 單一交換機連接的邊
            for conneceted_switch in self.switch_graph[datapath_id].keys():  # 逐個檢查已連接的 port
                switch_in_edges.add(int(datapath_id))   # 將本交換機加入已連接的交換機集合
                switch_in_edges.add(int(conneceted_switch)) # 將連接交換機加入已連接的交換機集合

        self.logger.info("Number of switches in edges : {:2d}".format(len(switch_in_edges)))    # 輸出已經連接的交換機統計資訊
        self.print_split_line('-', False)    # 打印分隔線
        for datapath_id in self.switch_ports.keys():    # 遍歷交換機的連接資訊
            if(self.switch_ports[datapath_id] != {}):   # 過濾已經連接的交換機
                ports_connect_string = ""
                for conneceted_port in self.switch_ports[datapath_id].keys():   # 遍歷交換機連接資訊
                    ports_connect_string += " port{} --> switch{:2s},".format(conneceted_port, self.switch_ports[datapath_id][conneceted_port])    # 顯示 port 與哪些交換機作連接
                self.logger.info("switch{:2d} with edges:{}".format(datapath_id, ports_connect_string[:-1]))    # 輸出連接資訊，-1 是為了過濾掉 ','
        
        self.find_position_host_may_existed()
        
        if(len(self.host_mac_learning.keys()) > 0):
            for mac in self.host_mac_learning.keys():
                self.logger.info("Mac address {} has learned, position : datapath{:2d} port{:2d}".format(mac,self.host_mac_learning[mac][0],self.host_mac_learning[mac][1]))
        self.print_split_line('=', False)   # 打印結束分隔線

    # 尋找主機可能存在的位置
    def find_position_host_may_existed(self):
        self.host_may_existed = {}
        message = "These position may exist host :"
        for datapath_id in self.switch_ports:
            connected_ports = self.switch_ports[datapath_id]
            set_connected_ports = set(list(connected_ports.keys()))
            set_ports_details = set(list(self.ports_details[datapath_id].keys()))
            host_may_exist = list(set_ports_details - set_connected_ports)
            if(len(host_may_exist) > 0):
                for port in host_may_exist:
                    if(datapath_id in self.host_may_existed.keys()):
                        port_A = self.host_may_existed[datapath_id]
                        port_A.append(port)
                        self.host_may_existed.update({datapath_id : port_A})
                    else:
                        self.host_may_existed.update({datapath_id : [port]})
                    message += " host{:2d}[port{:2d}],".format(datapath_id,port)
        self.logger.info(message[:-1])

    def init_flow_entry(self, datapath):
        
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        # Define the flow entry to be deleted (modify as needed)
        match = ofp_parser.OFPMatch()
        # Create an OFPFlowMod message to delete the flow entry
        modification_message = ofp_parser.OFPFlowMod(
            datapath=datapath,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY, match=match)
        # Send the message to delete the flow entry
        datapath.send_msg(modification_message)

        message = "Datapath {0} add table-miss flow entry with actions: send entire package to controller.".format(datapath.id)
        match = ofp_parser.OFPMatch()  
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow_entry(match, actions, 0, datapath, message)   # 優先級為 0

        message = "Datapath {:2d} add flow entry matched LLDP package with actions: send entire package to controller.".format(datapath.id)
        match = ofp_parser.OFPMatch(eth_type = 34525)  
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]
        self.add_flow_entry(match, actions, 1, datapath, message)   # 優先級為 2

        # self.logger.info("Datapath{:2d} init flow entry to original status".format(datapath.id))

    # 發送一個 flow mod 去添加一個 flow entry
    def add_flow_entry(self, match, actions, priority, datapath, message):
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
        
        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
        flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message , 屬於Controller-to-switch Messages
                datapath = datapath,    # 交換機
                match = match,  # 匹配項目
                cookie = 0, # Cookie 為 0
                command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
                idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
                hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
                priority = priority,   
                instructions = insturctions # 執行的動作
            )
        datapath.send_msg(flow_add_modification_message)    # 發送往交換機
        # self.logger.info(message)    # 顯示添加完成的 log

    # 將圖轉換為可以給 dijastra 演算法運算的狀態
    def transform_graph(self):
        graph = {}  # 清空 graph
        for datapath_id in self.switch_graph.keys():    # 遍歷拓樸上的交換機（可以存在未與任何交換機連接的節點）
            connected = self.switch_graph[datapath_id]  # 相對連接的節點
            new_connected = {}  # 更新的連接
            for switch in connected.keys():
                new_connected.update({switch: float(10000000/connected[switch])})   # 透過反比運算計算權重，公式 ＝ 10000000 / 可以用的 bandwidth
            graph.update({str(datapath_id): new_connected}) # 將交換機 ID 轉換為 字串作更新
        return graph    # 回傳新的圖
    
    # dijastra 取得特定點對其他在拓樸上連接的點的 cost
    def dijkstra(self,graph, start):
        start = str(start)
        distances = {node: float('inf') for node in graph}  # 預設所有節之間的距離為無限大
        distances[start] = 0    # 設定起點，起點與起點之間的距離為 0 
        priority_queue = [(0, start)]   # 因此 （cost, node） 對於起點來說是 （0, start）

        while priority_queue:   # 遍歷優先級 queue
            current_distance, current_node = heapq.heappop(priority_queue)  # 當前的距離以及節點，透過堆疊 pop 出最小元素

            if current_distance > distances[current_node]:  # 如果當前距離大於到當前節點的總據立舊部更新
                continue

            for neighbor, weight in graph[current_node].items():    # 將鄰居（有連接的點）與權重一起遍歷
                distance = current_distance + weight        # 當前距離加上權重
                if distance < distances[neighbor]:  # 如果小於與現在節點的距離，代表這條路徑效率比較好
                    distances[neighbor] = distance  # 更新當前距離
                    heapq.heappush(priority_queue, (distance, neighbor))    # push 進入堆積

        return distances    # 回傳個點到起點的 cost/distance
    
    # 透過 Dijkstra 尋找最短路徑
    def find_shortest_path_dijkstra(self,start,end,graph):  
        start = str(start)
        end = str(end)
        distances = {node: float('inf') for node in graph}  # 預設所有節之間的距離為無限大
        distances[start] = 0    # 設定起點，起點與起點之間的距離為 0 
        priority_queue = [(0, start)]   # 因此 （cost, node） 對於起點來說是 （0, start）

        previous_node = {node: None for node in graph}  # 紀錄路徑的前一個節點

        while priority_queue:
            current_distance, current_node = heapq.heappop(priority_queue)  # 當前的距離以及節點，透過堆疊 pop 出最小元素

            if current_distance > distances[current_node]:  # 如果當前距離大於到當前節點的總距離就不更新
                continue

            for neighbor, weight in graph[current_node].items():    # 將鄰居（有連接的點）與權重一起遍歷
                distance = current_distance + weight    # 當前距離加上權重

                if distance < distances[neighbor]:  # 如果小於與現在節點的距離，代表這條路徑效率比較好
                    distances[neighbor] = distance  # 更新當前距離
                    previous_node[neighbor] = current_node  # 更新當前節點到前一個節點
                    heapq.heappush(priority_queue, (distance, neighbor))     # push 進入堆積

        path = []   # 清空路徑
        current_node = end  # 設定終點
        while current_node is not None :    #　當節點有效
            path.insert(0, current_node)    # 加入新的節點
            current_node = previous_node[current_node]  # 添加節點道路敬

        return path # 回傳路徑

    def destination_does_not_valid(self,datapath,ingress_port,src_mac):
        self.print_split_line("=",True)
        self.logger.info("Now graph :")
        graph = self.transform_graph()

        for datapath_id in graph.keys():
            message = "Datapath{:2d} :".format(int(datapath_id))        
            for port in graph[datapath_id].keys():
                message += " port{:2d} : {:2.16f},".format(int(port),graph[datapath_id][port])
            self.logger.info(message[:-1])
        self.print_split_line("-",False)

        source_datapath = datapath.id
        costs = self.dijkstra(graph,source_datapath)
        flow = {}
        for datapath_id in self.host_may_existed.keys():
            # if(not (int(datapath_id) == datapath.id and ingress_port in self.host_may_existed[datapath_id])):
            destination_datapath = datapath_id
                
            message = "From datapath{:2d} to datapath {:2d} cost : {:2.16f}".format(source_datapath,destination_datapath,costs[str(destination_datapath)])
            self.logger.info(message)

            path_message = ""
            path = self.find_shortest_path_dijkstra(source_datapath,destination_datapath,graph)

            if(source_datapath == destination_datapath):
                for output_port in self.host_may_existed[datapath_id]:
                    if(output_port != ingress_port):
                        self.logger.info("switch{:2d}[port{:2d}] --> switch{:2d}[port{:2d}]".format(source_datapath,ingress_port,destination_datapath,output_port))
                        
                        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
                        
                        if(int(source_datapath) in flow.keys()):
                            data = flow[int(source_datapath)]
                            data.add(output_port)
                            flow.update({int(source_datapath) : data})
                        else:
                            flow.update({int(source_datapath) : set([output_port])})

                        message = "Datapath {:2d} add flow entry with match : eth_src = {} , actions : forwarding to port{:2d}".format(source_datapath, src_mac, output_port)
                        match = ofp_parser.OFPMatch(eth_src = src_mac)   # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address]為匹配項目
                        actions = [ofp_parser.OFPActionOutput(port = output_port)]
                        self.add_flow_entry(match, actions, 4, datapath, message)   # 優先級為
            else:
                for index,node in enumerate(path[:-1]):
                    start = node
                    end = path[index+1]

                    port = self.find_connected_port(start,end)
                    
                    if(index == 0):
                        link = "switch{:2d}[port{:2d}] --> switch{:2d}".format(int(start),port,int(end))
                        if(int(start) in flow.keys()):
                            data = flow[int(start)]
                            data.add(port)
                            flow.update({int(start) : data})
                        else:
                            flow.update({int(start) : set([port])})

                        if(int(end) in flow.keys()):
                            data = flow[int(end)]
                            flow.update({int(end) : data})
                        else:
                            flow.update({int(end) : set()})
                        path_message += link
                    else:
                        link = "[port{:2d}] --> switch{:2d}".format(port,int(end))
                        if(int(start) in flow.keys()):
                            data = flow[int(start)]
                            data.add(port)
                            flow.update({int(start) : data})
                        else:
                            flow.update({int(start) : set([port])})
                        path_message += link

                for output_port in self.host_may_existed[datapath_id]:
                    if(int(datapath_id) in flow.keys()):
                        data = flow[int(datapath_id)]
                        data.add(output_port)
                        flow.update({int(datapath_id) : data})
                    else:
                        flow.update({int(datapath_id) : set([output_port])})
                    self.logger.info(path_message + "[port{:2d}]".format(output_port))

        self.print_split_line("-",False)

        self.logger.info(flow)

        self.update_flooding_flow_entry(flow,src_mac,4)
            
        self.print_split_line("=",False)

    def destination_does_valid(self,src_mac,dst_mac):
        source_datapth_id = self.host_mac_learning[src_mac][0]
        source_datapath = self.datapaths[source_datapth_id]
        source_port = self.host_mac_learning[src_mac][1]

        destination_datapath_id = self.host_mac_learning[dst_mac][0]
        destination_datapath = self.datapaths[destination_datapath_id]
        destination_port = self.host_mac_learning[dst_mac][1]

        if(destination_datapath_id == source_datapth_id):
            datapath = destination_datapath
            ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

            message = "Datapath {:2d} add flow entry with match : eth_type= 2054, eth_src = {}, eth_dst = {}, actions : forwarding to port{:2d}".format(source_datapth_id,src_mac,dst_mac,destination_port)
            match = ofp_parser.OFPMatch(eth_src = src_mac, eth_dst = dst_mac)
            actions = [ofp_parser.OFPActionOutput(port = destination_port)]
            self.add_flow_entry(match, actions, 5, datapath, message)   # 優先級為 5

            message = "Datapath {:2d} add flow entry with match : eth_type= 2054, eth_src = {}, eth_dst = {}, actions : forwarding to port{:2d}".format(source_datapth_id,dst_mac,src_mac,source_port)
            match = ofp_parser.OFPMatch(eth_src = dst_mac, eth_dst = src_mac)
            actions = [ofp_parser.OFPActionOutput(port = source_port)]
            self.add_flow_entry(match, actions, 5, datapath, message)   # 優先級為 5
        else:
            graph = self.transform_graph()
            costs = self.dijkstra(graph,source_datapth_id)
            path = self.find_shortest_path_dijkstra(source_datapth_id,destination_datapath_id,graph)
            
            flow = []
            self.logger.info("Source mac address {} from datapth{:2d} to destination mac address {} from Datapath{:2d} with cost : {:2.16f}".format(src_mac,source_datapth_id,dst_mac,destination_datapath_id,costs[str(destination_datapath_id)]))
            path_message = ""
            for index,node in enumerate(path[:-1]):
                start = node
                end = path[index+1]

                port = self.find_connected_port(start,end)
                if(index == 0):
                    link = "switch{:2d}[port{:2d}] --> switch{:2d}".format(int(start),port,int(end))
                    path_message += link
                else:
                    link = "[port{:2d}] --> switch{:2d}".format(port,int(end))
                    path_message += link
                flow.append([int(start),port])

            path_message += "[port{:2d}]".format(destination_port)
            flow.append([int(destination_datapath_id),destination_port])
            self.logger.info(path_message)
            
            for data in flow:
                datapath = self.datapaths[data[0]]
                output_port = data[1]

                ofp_parser = datapath.ofproto_parser
                
                message = "Datapath{:2d} add flow with match : eth_src = {}, eth_dst = {} ,actions : forwarding to port{:2d}".format(data[0],src_mac,dst_mac,output_port)
                match = ofp_parser.OFPMatch(eth_src = src_mac, eth_dst = dst_mac)
                actions = [ofp_parser.OFPActionOutput(port = output_port)]

                self.delete_flow_entry(datapath,match,5)
                self.add_flow_entry(match, actions, 5, datapath, message)   # 優先級為 5

                self.logger.info(message)
            
            costs = self.dijkstra(graph,destination_datapath_id)
            path = self.find_shortest_path_dijkstra(destination_datapath_id,source_datapth_id,graph)
            
            flow = []
            self.logger.info("Source mac address {} from datapth{:2d} to destination mac address {} from Datapath{:2d} with cost : {:2.16f}".format(dst_mac,destination_datapath_id,src_mac,source_datapth_id,costs[str(destination_datapath_id)]))
            path_message = ""
            for index,node in enumerate(path[:-1]):
                start = node
                end = path[index+1]

                port = self.find_connected_port(start,end)
                if(index == 0):
                    link = "switch{:2d}[port{:2d}] --> switch{:2d}".format(int(start),port,int(end))
                    path_message += link
                else:
                    link = "[port{:2d}] --> switch{:2d}".format(port,int(end))
                    path_message += link
                flow.append([int(start),port])

            path_message += "[port{:2d}]".format(source_port)
            flow.append([int(source_datapth_id),source_port])
            self.logger.info(path_message)
            
            for data in flow:
                datapath = self.datapaths[data[0]]
                output_port = data[1]

                ofp_parser = datapath.ofproto_parser
                
                message = "Datapath{:2d} add flow with match : eth_src = {}, eth_dst = {} ,actions : forwarding to port{:2d}".format(data[0],dst_mac,src_mac,output_port)
                match = ofp_parser.OFPMatch(eth_src = dst_mac, eth_dst = src_mac)
                actions = [ofp_parser.OFPActionOutput(port = output_port)]

                # self.delete_flow_entry(datapath,match,5)
                self.add_flow_entry(match, actions, 5, datapath, message)   # 優先級為 5

                self.logger.info(message)



    def find_connected_port(self,datapath_id,connected_datapath_id):
        datapath_id = int(datapath_id)
        connected_datapath_id = int(connected_datapath_id)
        for port in self.switch_ports[datapath_id].keys():
            if(self.switch_ports[datapath_id][port] == str(connected_datapath_id)):
                # self.logger.info("Datapath{:2d} to datapath{:2d} with port{:2d}".format(datapath_id,connected_datapath_id,port))
                port = int(port)
                return port

    def delete_flow_entry(self,datapath,match,priority):
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser

        instructions = []
        flow_mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=instructions,
            command=ofproto.OFPFC_DELETE,
            out_port=ofproto.OFPP_ANY,
            out_group=ofproto.OFPG_ANY,
        )
        datapath.send_msg(flow_mod)
    
    def update_flooding_flow_entry(self,flow,src_mac_address,priority):
        for datapath_id in flow.keys():
            datapath = self.datapaths[datapath_id]
            ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
            match = ofp_parser.OFPMatch(eth_src = src_mac_address)

            self.delete_flow_entry(datapath,match,priority)

            ports = flow[datapath_id]
            message = "Datapath{:2d} add flow entry with match : eth_src = {}, action :forwarding package to ports : {}".format(datapath_id,src_mac_address,str(ports))
            actions =[]
            for port in ports:
                actions.append(ofp_parser.OFPActionOutput(port = port))
            self.add_flow_entry(match, actions, priority, datapath, message)
            self.logger.info(message)

    def add_flooding_flow_entry(self,src_mac):
        graph = self.transform_graph()  # 

        source_datapath_id = self.host_mac_learning[src_mac][0]
        source_datapath_port = self.host_mac_learning[src_mac][1]
        source_datapath = self.datapaths[source_datapath_id]

        flow = {}

        for datapath_id in self.host_may_existed.keys():
            self.logger.info(datapath_id)
            destination_datapath_id = datapath_id
            path = self.find_shortest_path_dijkstra(source_datapath,destination_datapath_id,graph)

            if(source_datapath_id == destination_datapath_id):
                for output_port in self.host_may_existed[datapath_id]:
                    if(output_port != source_datapath_port):
                        
                        ofp_parser = source_datapath.ofproto_parser    # 創建和解析 OpenFlow message
                        
                        if(int(source_datapath_id) in flow.keys()):
                            data = flow[int(source_datapath_id)]
                            data.add(output_port)
                            flow.update({int(source_datapath_id) : data})
                        else:
                            flow.update({int(source_datapath_id) : set([output_port])})

                        message = "Datapath {:2d} add flow entry with match : eth_src = {} , actions : forwarding to port{:2d}".format(source_datapath_id, src_mac, output_port)
                        match = ofp_parser.OFPMatch(eth_src = src_mac)   # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address]為匹配項目
                        actions = [ofp_parser.OFPActionOutput(port = output_port)]
                        self.add_flow_entry(match, actions, 4, source_datapath, message)   # 優先級為

            else:
                for index,node in enumerate(path[:-1]):
                    start = node
                    end = path[index+1]

                    port = self.find_connected_port(start,end)
                    
                    if(index == 0):
                        if(int(start) in flow.keys()):
                            data = flow[int(start)]
                            data.add(port)
                            flow.update({int(start) : data})
                        else:
                            flow.update({int(start) : set([port])})

                        if(int(end) in flow.keys()):
                            data = flow[int(end)]
                            flow.update({int(end) : data})
                        else:
                            flow.update({int(end) : set()})
                    else:
                        if(int(start) in flow.keys()):
                            data = flow[int(start)]
                            data.add(port)
                            flow.update({int(start) : data})
                        else:
                            flow.update({int(start) : set([port])})
                
                for output_port in self.host_may_existed[datapath_id]:
                    if(int(datapath_id) in flow.keys()):
                        data = flow[int(datapath_id)]
                        data.add(output_port)
                        flow.update({int(datapath_id) : data})
                    else:
                        flow.update({int(datapath_id) : set([output_port])})
            
            self.update_flooding_flow_entry(flow,src_mac,3)



    # 監控線程執行的函數，每 5 秒執行一次
    def every_five_second_monitoring(self):
        while(True):
            try:
                for datapath_id in self.datapaths:  # 更新拓樸變化
                    self.send_port_desc_stats_request(self.datapaths[datapath_id])  # 發送 EventOFPPortDescStatsRequest 觸發 EventOFPPortDescStatsReply 事件更新拓樸
                    self.send_port_status_request(self.datapaths[datapath_id])

                
                self.show_topology_lldp()    # 顯示拓樸變化
            except KeyError:
                self.logger.info("Topology discovery happens KeyError")
            hub.sleep(5)    # 停止 5 秒