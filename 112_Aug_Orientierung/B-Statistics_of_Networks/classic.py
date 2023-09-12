from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER,DEAD_DISPATCHER
from ryu.controller.handler import set_ev_cls

from ryu.topology.api import get_switch, get_link
import json
import csv
import shutil
from ryu.lib import hub
import time
from ryu.lib.packet import ether_types
from ryu.lib.packet import packet, ethernet, lldp
from collections import OrderedDict


from operator import attrgetter

class Flow_entries_management(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # 確定控制器所用OpenFlow版本

    # 交換機啟動得初始化函數
    def __init__(self,*args,**kwargs):
        super(Flow_entries_management,self).__init__(*args,**kwargs)
        self.discover_thread = hub.spawn(self.every_five_second_monitoring)     # 建立一個 thread 用於每 5 秒的監控

        self.datapaths={}   # 儲存整個網路的 Datapath 物件

        self.start_time = time.time()   # 紀錄啟動時間
        self.host_mac_address = ["00:04:00:00:00:01", "00:04:00:00:00:02", "00:04:00:00:00:03", "00:04:00:00:00:04"]   # 主機的 mac address
        self.host_ip_address = ["10.0.0.10", "10.0.0.11", "10.0.0.12", "10.0.0.13"]    # 主機的 ip address

        self.switch_features_path= './configuration/switch_features.csv'    # 交換機 feature 文檔路徑
        self.switch_features=[] # 整個網路的交換機 feature 
        self.clear_switch_features()    # 清空交換機 feature 文檔

        self.ports_statistic_path = './configuration/ports_statistic.json' # port 統計資訊的資料配置文檔路徑
        self.ports_statistic = {}   # 整個網路的交換機的 port 統計資訊
        self.clear_port_statistic() # 清空 port 統計資訊的配置文檔

    # switch_features_handler 響應 OFPT_FEATURES_REPLY
    @set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
    def switch_features_handler(self,event):
        # 取得資料 
        message = event.msg     # 事件的訊息
        datapath = message.datapath   # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        self.send_port_desc_stats_request(datapath) # 發送 OFPPortDescStatsRequest 取得 port 的配置統計資訊
        self.send_port_stats_request(datapath)  # 發送 OFPPortStatsRequest 取得 port 的統計資訊
        self.send_flow_stats_request(datapath)  # 發送 OFPFlowStatsRequest 取得 flow entry 的統計資訊
        self.datapaths.update({datapath.id:datapath})   # 初始化交換機物件

        # 設定 table-miss flow entry : 
        match = ofp_parser.OFPMatch()   # 匹配所有封包
        actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]   # 將整個封包發送到控制器
        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
        flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message ,屬於Controller-to-switch Messages
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
        self.logger.debug("Datapath {0} add table-miss flow entry with actions: send entire package to controller.".format(datapath.id))    # 顯示添加完成的 log
        
        self.add_meter_entry(1,100,datapath)    # 限制流量速率為 100, meter_ID 為 1
        self.add_meter_entry(2,200,datapath)    # 限制流量速率為 200, meter_ID 為 2
        self.add_meter_entry(3,300,datapath)    # 限制流量速率為 300, meter_ID 為 3
        self.add_meter_entry(4,400,datapath)    # 限制流量速率為 400, meter_ID 為 4

        switch_features = [message.datapath_id,message.n_buffers,message.n_tables,message.auxiliary_id,message.capabilities] # 取得 features
        self.switch_features.append(switch_features)    # 添加 features 在 switch_features
        self.write_switch_features() # 寫入 switch_features.csv
        self.show_switch_features_and_configuration(datapath)   # 顯示交換機 feature 的能力

        if(datapath.id < 5):    # 對於所有連接到主機的交換機 id < 5
            for index in range(len(self.host_mac_address)): # 遍歷所有主機的 mac address
                if(index == (datapath.id-1)):   # 如果是對應連接的主機
                    self.add_eth_src_flow_entry(self.host_mac_address[index], 2, datapath)    # 將封包發送到 port 2 (匹配 eth_src = [self.host_mac_address[index]])
                    self.add_ipv4_src_flow_entry(self.host_ip_address[index], 2, datapath)    # 將封包發送到 port 2 (匹配 ipv4_src = [self.host_ip_address[index]])
                else:   # 對於來源非連接主機
                    self.add_eth_src_flow_entry(self.host_mac_address[index], 1, datapath)    # 發送到連接主機
                    self.add_ipv4_src_flow_entry(self.host_ip_address[index], 1, datapath)    # 發送到連接主機

        # 對於中層交換機
        if(datapath.id > 4 and datapath.id < 7):
            branch =[   # 分支輸出 port
                [2, 3],  # host1 : 5 --> 2/9  6 --> 2/10
                [1, 3],  # host2 : 5 --> 1/9  6 --> 1/10
                [1, 2],  # host1 : 5 --> 1/2  6 --> 1/2
                [1, 2]   # host1 : 5 --> 1/2  6 --> 1/2
            ]
            
            for index in range(len(self.host_mac_address)): # 依據 branch 和 address 添加 flow entry
                self.add_eth_src_branch_flow_entry(self.host_mac_address[index], branch[index][0], branch[index][1], datapath) # 添加具有分支輸出動作且匹配項目只有來源 mac_address 的 flow entry
                self.add_ipv4_src_branch_flow_entry(self.host_ip_address[index], branch[index][0], branch[index][1], datapath) # 添加具有分支輸出動作且匹配項目只有來源 ip_address 的 flow entry

            for dst in [2, 3]:   # 對於 host3 和 host 4
                self.add_eth_dst_flow_entry(self.host_mac_address[dst], 3, datapath)  # 添加 X --> host3/4 的 flow entry，match with mac_address
                self.add_ipv4_dst_flow_entry(self.host_ip_address[dst], 3, datapath)  # 添加 X --> host3/4 的 flow entry，match with ipv4_address and tcp port

                self.add_eth_src_dst_flow_entry(self.host_mac_address[dst], self.host_mac_address[0], 1, datapath) # 添加 host3/4 --> host1 的 flow entry，match with mac_address
                self.add_eth_src_dst_flow_entry(self.host_mac_address[dst], self.host_mac_address[1], 2, datapath) # 添加 host3/4 --> host2 的 flow entry，match with mac_address

                self.add_ipv4_src_dst_flow_entry(self.host_ip_address[dst], self.host_ip_address[0], 1, datapath)  # 添加 host3/4 --> host1 的 flow entry，match with ipv4_address and tcp port
                self.add_ipv4_src_dst_flow_entry(self.host_ip_address[dst], self.host_ip_address[1], 2, datapath)  # 添加 host3/4 --> host2 的 flow entry，match with ipv4_address and tcp port

            self.add_eth_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[1], 2, datapath)   # 添加 host1 --> host2 的 match with mac_address
            self.add_eth_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[0], 1, datapath)   # 添加 host2 --> host1 的 match with mac_address

            self.add_ipv4_src_dst_flow_entry(self.host_ip_address[0], self.host_ip_address[1], 2, datapath)    # 添加 host1 --> host2 的 flow entry，match with ipv4_address and tcp port
            self.add_ipv4_src_dst_flow_entry(self.host_ip_address[1], self.host_ip_address[0], 1, datapath)    # 添加 host2 --> host1 的 flow entry，match with ipv4_address and tcp port

        # 對於中層交換機
        if(datapath.id > 6 and datapath.id < 9):    
            branch =[   # 分支輸出 port
                [1, 2],  # host1 : 7 --> 3/4  8 --> 3/4 
                [1, 2],  # host1 : 7 --> 3/4  6 --> 3/4
                [2, 3],  # host1 : 7 --> 4/9  6 --> 4/10
                [1, 3]   # host1 : 7 --> 3/9  6 --> 3/10
            ]
            for index in range(len(self.host_mac_address)): # 依據 branch 和 address 添加 flow entry
                self.add_eth_src_branch_flow_entry(self.host_mac_address[index], branch[index][0], branch[index][1], datapath)     # 添加具有分支輸出動作且匹配項目只有來源 mac_address 的 flow entry
                self.add_ipv4_src_branch_flow_entry(self.host_ip_address[index], branch[index][0], branch[index][1], datapath)     # 添加具有分支輸出動作且匹配項目只有來源 ip_address 的 flow entry

            for dst in [0, 1]:   # 對於 host1 和 host2
                self.add_eth_dst_flow_entry(self.host_mac_address[dst], 3, datapath)  # 添加 X --> host1/2 的 flow entry，match with mac_address
                self.add_ipv4_dst_flow_entry(self.host_ip_address[dst], 3, datapath)  # 添加 X --> host1/2 的 flow entry，match with ipv4_address and tcp port

                self.add_eth_src_dst_flow_entry(self.host_mac_address[dst], self.host_mac_address[2], 1, datapath) # 添加 host1/2 --> host3 的 flow entry，match with mac_address
                self.add_eth_src_dst_flow_entry(self.host_mac_address[dst], self.host_mac_address[3], 2, datapath) # 添加 host1/2 --> host4 的 flow entry，match with mac_address

                self.add_ipv4_src_dst_flow_entry(self.host_ip_address[dst], self.host_ip_address[2], 1, datapath)  # 添加 host1/2 --> host3 的 flow entry，match with ipv4_address and tcp port
                self.add_ipv4_src_dst_flow_entry(self.host_ip_address[dst], self.host_ip_address[3], 2, datapath)  # 添加 host1/2 --> host4 的 flow entry，match with ipv4_address and tcp port

            self.add_eth_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[3], 2, datapath)   # 添加 host3 --> host4 的 match with mac_address
            self.add_eth_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[2], 1, datapath)   # 添加 host4 --> host3 的 match with mac_address

            self.add_ipv4_src_dst_flow_entry(self.host_ip_address[2], self.host_ip_address[3], 2, datapath)    # 添加 host3 --> host4 的 flow entry，match with ipv4_address and tcp port
            self.add_ipv4_src_dst_flow_entry(self.host_ip_address[3], self.host_ip_address[2], 1, datapath)    # 添加 host4 --> host3 的 flow entry，match with ipv4_address and tcp port

        if(datapath.id > 8):
            message = "Datapath {:2d} add flow entry with match : in_port = {} ,actions : forwarding to port {}".format(datapath.id,1,2)
            match = ofp_parser.OFPMatch(in_port = 1)
            actions = [ofp_parser.OFPActionOutput(port = 2)]
            self.add_flow_entry(match,actions,1,datapath,message)   # 9 --> 7 / 10 --> 8

            message = "Datapath {:2d} add flow entry with match : in_port = {} ,actions : forwarding to port {}".format(datapath.id,2,1)
            match = ofp_parser.OFPMatch(in_port = 2)
            actions = [ofp_parser.OFPActionOutput(port = 1)]    # 9 --> 5 / 10 --> 6
            self.add_flow_entry(match,actions,1,datapath,message)

        # H1🡨🡪H3 with rate 200Mbps
        if(datapath.id == 1):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[2],2,2,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[0],1,2,datapath)

        if(datapath.id == 5):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[2],3,2,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[0],1,2,datapath)

        if(datapath.id == 9):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[2],2,2,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[0],1,2,datapath)

        if(datapath.id == 7):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[2],1,2,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[0],3,2,datapath)

        if(datapath.id == 3):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[2],1,2,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[0],2,2,datapath)
        
        # H2🡨🡪H3 with rate 100Mbps
        if(datapath.id == 2):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[2],3,1,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[1],1,1,datapath)

        if(datapath.id == 6):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[2],3,1,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[1],2,1,datapath)

        if(datapath.id == 10):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[2],2,1,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[1],1,1,datapath)

        if(datapath.id == 8):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[2],1,1,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[1],3,1,datapath)

        if(datapath.id == 3):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[2],1,1,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[2],self.host_ip_address[1],3,1,datapath)

        # self.add_meter_entry(3,250,datapath)
        # H1🡨🡪H4 with rate 300Mbps
        if(datapath.id == 1):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[3],2,3,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[0],1,3,datapath)

        if(datapath.id == 5):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[3],3,3,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[0],1,3,datapath)

        if(datapath.id == 9):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[3],2,3,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[0],1,3,datapath)

        if(datapath.id == 7):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[3],2,3,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[0],3,3,datapath)

        if(datapath.id == 4):
            self.add_limited_rate_flow_entry(self.host_ip_address[0],self.host_ip_address[3],1,3,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[0],2,3,datapath)
        
        # self.add_meter_entry(4,350,datapath)
        # H2🡨🡪H4 with rate 400Mbps
        if(datapath.id == 2):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[3],3,4,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[1],1,4,datapath)

        if(datapath.id == 6):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[3],3,4,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[1],2,4,datapath)

        if(datapath.id == 10):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[3],2,4,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[1],1,4,datapath)

        if(datapath.id == 8):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[3],2,4,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[1],3,4,datapath)

        if(datapath.id == 4):
            self.add_limited_rate_flow_entry(self.host_ip_address[1],self.host_ip_address[3],1,4,datapath)
            self.add_limited_rate_flow_entry(self.host_ip_address[3],self.host_ip_address[1],3,4,datapath)
        
    # 響應封包進入控制器的事件
    @set_ev_cls(ofp_event.EventOFPPacketIn,MAIN_DISPATCHER)
    def packet_in_handler(self,event):
        message = event.msg # message of event
        datapath = event.msg.datapath    # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        package = packet.Packet(data = message.data)  # 取得封包
        datapath_id = datapath.id   # 來源的交換機
        ingress_port  = message.match['in_port']    # 輸入的 port

        package_ethernet = package.get_protocol(ethernet.ethernet)  # ethernet frame

    # OFPPortDescStatsRequest 的響應，統計 port 的資訊
    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, event):
        # 取得訊息
        datapath = event.msg.datapath    # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息

        ports = {}
        # 遍歷 event 中收到的每個 port 的統計訊息
        for statistic in event.msg.body:
            if statistic.port_no <= ofproto.OFPP_MAX:    # 如果 port_no(port number) 小於或等於 OFPP_MAX（最大的 port number ) -> 表示該 port 有效且不是 reserved port
                
                config = format(int(statistic.config), '04b')   # 前四碼代表不同的配置
                OFPPC_PORT_DOWN = "DOWN" if int(config[3]) == 1 else "UP"       # port down or up
                OFPPC_NO_RECV = "NOT RECEIVE PACKETS" if int(config[2]) == 1  else "CAN RECEIVE PACKETS"    # 可不可以接收 packets
                OFPPC_NO_FWD = "NOT FORWARD PACKETS" if int(config[1]) else "CAN FORWARD PACKETS"   # 可不可以轉發 packets
                OFPPC_NO_PACKET_IN = "NOT FORWARD PACKETS".upper() if int(config[0]) else "can send packet-in messages".upper() # 可不可以轉發 packets_in
                
                port_state = "LIVE" if statistic.state else "NOT LIVE"  # port 的活動狀態
                
                curr = statistic.curr   # 當前速度支援
                OFPF_10MB_HD = "SUPPORTED" if bool(curr & 1) else "NOT_SUPPORTED"   # 通常是 10 MB
                OFPF_10MB_FD = "SUPPORTED" if bool(curr & (1 << 9)) else "NOT_SUPPORTED" 

                advertised = statistic.advertised   # 進階功能支援
                if(advertised == 0):
                    self.logger.info("advertised : No Advertised Features")
                else:
                    OFPPF_10MB_HD = "SUPPORTED" if bool(advertised & (1 << 0)) else "NOT_SUPPORTED"            # 10 Mb half-duplex rate support.
                    OFPPF_10MB_FD = "SUPPORTED" if bool(advertised & (1 << 1)) else "NOT_SUPPORTED"          # 10 Mb full-duplex rate support.
                    OFPPF_100MB_HD = "SUPPORTED" if bool(advertised & (1 << 2)) else "NOT_SUPPORTED"         # 100 Mb half-duplex rate support.
                    OFPPF_100MB_FD = "SUPPORTED" if bool(advertised & (1 << 3)) else "NOT_SUPPORTED"         # 100 Mb full-duplex rate support.
                    OFPPF_1GB_HD = "SUPPORTED" if bool(advertised & (1 << 4)) else "NOT_SUPPORTED"           # 1 Gb half-duplex rate support.
                    OFPPF_1GB_FD = "SUPPORTED" if bool(advertised & (1 << 5)) else "NOT_SUPPORTED"           # 1 Gb full-duplex rate support.

                OFPPF_10MB_HD = "SUPPORTED" if bool(advertised & (1 << 0)) else "NOT_SUPPORTED"            # 10 Mb half-duplex rate support.
                OFPPF_10MB_FD = "SUPPORTED" if bool(advertised & (1 << 1)) else "NOT_SUPPORTED"          # 10 Mb full-duplex rate support.
                OFPPF_100MB_HD = "SUPPORTED" if bool(advertised & (1 << 2)) else "NOT_SUPPORTED"         # 100 Mb half-duplex rate support.
                OFPPF_100MB_FD = "SUPPORTED" if bool(advertised & (1 << 3)) else "NOT_SUPPORTED"         # 100 Mb full-duplex rate support.
                OFPPF_1GB_HD = "SUPPORTED" if bool(advertised & (1 << 4)) else "NOT_SUPPORTED"           # 1 Gb half-duplex rate support.
                OFPPF_1GB_FD = "SUPPORTED" if bool(advertised & (1 << 5)) else "NOT_SUPPORTED"           # 1 Gb full-duplex rate support.

                supported = statistic.supported # 支援功能
                peer = statistic.peer   # 忘了

                curr_speed =statistic.curr_speed    # 當前速率
                max_speed = statistic.max_speed # 最大支援速率

                update_data = { # 更新資料
                    statistic.port_no : {
                        "hw_addr" : statistic.hw_addr,
                        "name" : statistic.name.decode(),
                        "config" : config,
                        "OFPPC_PORT_DOWN" : OFPPC_PORT_DOWN,
                        "OFPPC_NO_RECV" : OFPPC_NO_RECV,
                        "OFPPC_NO_FWD": OFPPC_NO_FWD,
                        "OFPPC_NO_PACKET_IN" : OFPPC_NO_PACKET_IN,
                        "port_state" : port_state,
                        "curr" : curr,
                        "supported" : supported,
                        "peer" : peer,
                        "advertised" : advertised,
                        "OFPPF_10MB_HD" : OFPPF_10MB_HD,
                        "OFPPF_10MB_FD" : OFPPF_10MB_FD,
                        "OFPPF_100MB_HD": OFPPF_100MB_HD,
                        "OFPPF_100MB_FD" : OFPPF_100MB_FD,
                        "OFPPF_1GB_HD" : OFPPF_1GB_HD,
                        "OFPPF_1GB_FD" : OFPPF_1GB_FD,
                        "max_speed" : max_speed,
                        "curr_speed" : curr_speed
                    }
                }
                if(datapath.id in self.ports_statistic.keys() and statistic.port_no in self.ports_statistic[datapath.id].keys()):
                    if('rx_bytes' in self.ports_statistic[datapath.id][statistic.port_no].keys()):  #處理存在統計資訊的情況
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

                    if('free_bandwidth_rx' in self.ports_statistic[datapath.id][statistic.port_no].keys()): # 處理存在當前 bandwidth 計算的情況
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
        self.write_port_statistic() # 將 port 統計資訊寫入文檔

        # iperfudp 會觸發 EventOFPPortStatsReply 事件進行統計
    
    # 取得 port 的統計資訊
    @set_ev_cls(ofp_event.EventOFPPortStatsReply,MAIN_DISPATCHER)
    def _port_stats_reply_handler(self,event):
        ofproto = event.msg.datapath.ofproto    #  OpenFlow 協議相關訊息
        ports = event.msg.body  #  交換機上的 port
        for port in ports:
            port_number = port.port_no
            datapath_id = event.msg.datapath.id
            if(port_number < ofproto.OFPP_MAX):
                rx_packets = port.rx_packets    # 接收到的總 packet 總數
                tx_packets = port.tx_packets    # 傳輸的總 packet 總數
                rx_bytes = port.rx_bytes    # 接收到的 bytes 總數
                tx_bytes = port.tx_bytes    # 傳輸的 bytes 總數
                rx_errors = port.rx_errors  # 接收到的 error 總數
                tx_errors = port.tx_errors  # 傳輸的 error 總數

                if('rx_bytes' in self.ports_statistic[datapath_id][port_number].keys()):
                    now_time = time.time()  # 取得現在時間
                    elapsed_time = now_time - self.start_time   # 取得執行時間
                    last_time = float(self.ports_statistic[datapath_id][port_number]['update_time'])    # 上一次的更新時間
                    interval_time = elapsed_time - last_time    # 兩次的時間間隔
                    
                    rx_bytes_diff = rx_bytes - self.ports_statistic[datapath_id][port_number]['rx_bytes']   # 接收到的總 bytes 總數差異
                    tx_bytes_diff = tx_bytes - self.ports_statistic[datapath_id][port_number]['tx_bytes']   # 傳輸的總 bytes 總數差異

                    port_statistic = self.ports_statistic[datapath_id][port_number] # port 的統計資訊

                    occupied_bandwidth_rx = (rx_bytes_diff / interval_time) * 8 # bytes 轉換為 bits，取得接收的 bandwidth，也就是已經佔用的 bandwidth
                    occupied_bandwidth_tx = (tx_bytes_diff / interval_time) * 8 # bytes 轉換為 bits，取得傳輸的 bandwidth，也就是已經佔用的 bandwidth
                    
                    self.ports_statistic[datapath_id][port_number].update({'occupied_bandwidth_rx' : occupied_bandwidth_rx})    # 更新統計資訊
                    self.ports_statistic[datapath_id][port_number].update({'occupied_bandwidth_tx' : occupied_bandwidth_tx})    

                    free_bandwidth_rx = abs(port_statistic['curr_speed'] - occupied_bandwidth_rx)   # 計算空閒的 bandwidth
                    free_bandwidth_tx = abs(port_statistic['curr_speed'] - occupied_bandwidth_tx)   # 計算空閒的 bandwidth

                    self.ports_statistic[datapath_id][port_number].update({'free_bandwidth_rx' : free_bandwidth_rx})    # 更新統計資訊
                    self.ports_statistic[datapath_id][port_number].update({'free_bandwidth_tx' : free_bandwidth_tx})

                    # 解註解查看 port 統計資訊
                    # self.show_port_statistic_information(datapath_id,port_number,True)
                
                now_time = time.time()  # 取得現在時間
                elapsed_time = now_time - self.start_time   # 取得執行時間
                self.ports_statistic[datapath_id][port_number].update({'update_time' : elapsed_time})   # 更新執行時間
                self.ports_statistic[datapath_id][port_number].update({'rx_packets' : rx_packets})  # 接收到的總 packet 總數
                self.ports_statistic[datapath_id][port_number].update({'tx_packets' : tx_packets})  # 傳輸的總 packet 總數
                self.ports_statistic[datapath_id][port_number].update({'rx_bytes' : rx_bytes})  # 接收到的 bytes 總數
                self.ports_statistic[datapath_id][port_number].update({'tx_bytes' : tx_bytes})  #傳 輸的 bytes 總數
                self.ports_statistic[datapath_id][port_number].update({'rx_errors' : rx_errors})    # 接收到的 error 總數
                self.ports_statistic[datapath_id][port_number].update({'tx_errors' : tx_errors})    # 傳輸的 error 總數
                self.write_port_statistic()

                # 解註解查看 port 統計資訊
                # self.show_port_statistic_information(datapath_id,port_number,False)

    # 嚮應 ofp_event.EventOFPFlowStatsReuest
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply,MAIN_DISPATCHER)
    def flow_stats_reply_handler(self,event):
        flow_entries = event.msg.body   # flow table(?) 該交換機的所有 flow enties
        datapath = event.msg.datapath    # 交換機（datapath）結構

        self.print_split_line("=",True) # 起始分隔線
        self.logger.info("Datapath{:2d} with {:3d} flow entries: ".format(datapath.id,len(flow_entries)))   # 交換機名稱以及 flow entry 總數目
        
        for index,flow_statistic in enumerate(flow_entries):    # 遍歷 flow table
            self.print_split_line("-",True) # 內部起始分隔線

            now_time = time.time()  # 取得現在時間
            elapsed_time = now_time - self.start_time   # 取得執行時間

            self.logger.info("Datapath{:2d} , {:3d}th flow entry in time {:3.2f} second: ".format(datapath.id,index+1,elapsed_time))    # 再次顯示時間
            cookie = flow_statistic.cookie  # cookie
            table_id = flow_statistic.table_id  # flow table _id
            duration_sec = flow_statistic.duration_sec  # 存活時間（以秒為單位）
            priority = flow_statistic.priority  # flow entry 優先級

            idle_timeout = flow_statistic.idle_timeout  # 未匹配過期時間
            hard_timeout = flow_statistic.hard_timeout  # 存活過期時間
            
            flags = flow_statistic.flags    # 標誌
            length = flow_statistic.length  # 長度
            
            packet_count = flow_statistic.packet_count  # 匹配到的封包數量統計
            byte_count = flow_statistic.byte_count  # 匹配到的封包 bytes 數量統計

            match = flow_statistic.match    # match filed
            instructions = flow_statistic.instructions  # 執行動作

            # 格式化輸出
            self.logger.info("table_id     : {:8d}  priority     : {:8d}  duration_sec : {:8d}  cookie       : {:8d}".format(table_id,priority,duration_sec,cookie))
            self.logger.info("flags        : {:16d}  length       : {:16d}".format(flags,length))
            self.logger.info("idle_timeout : {:16d}  hard_timeout : {:16d}".format(idle_timeout,hard_timeout))
            self.logger.info("packet_count : {:16d}  byte_count   : {:16d}".format(packet_count,byte_count))
            
            # 輸出 match field
            self.logger.info("")
            match_field_string = "|"
            match_value_string = "|"
            for match_field in match.to_jsondict()['OFPMatch']['oxm_fields']:   # 根據類型決定格式長度
                field = match_field['OXMTlv']['field']
                value = match_field['OXMTlv']['value']
                if(field == 'eth_type'):
                    match_field_string += ' eth_type |'
                    match_value_string += " {:8s} |".format(str(value))
                if(field == 'ip_proto'):
                    match_field_string += ' ip_proto |'
                    match_value_string += " {:8d} |".format(value)
                if(field == 'eth_src'):
                    match_field_string += '      eth_src      |'
                    match_value_string += " {:17s} |".format(value)
                if(field == 'eth_dst'):
                    match_field_string += '      eth_dst      |'
                    match_value_string += " {:17s} |".format(value)
                if(field == 'ipv4_src'):
                    match_field_string += '  ipv4_src  |'
                    match_value_string += " {:10s} |".format(value)
                if(field == 'ipv4_dst'):
                    match_field_string += '  ipv4_dst  |'
                    match_value_string += " {:10s} |".format(value)
                if(field == 'tcp_dst'):
                    match_field_string += ' tcp_dst |'
                    match_value_string += " {:7d} |".format(value)
                if(field == 'in_port'):
                    match_field_string += ' in_port |'
                    match_value_string += " {:7d} |".format(value)
            
            if(len(match.to_jsondict()['OFPMatch']['oxm_fields']) > 0):
                self.logger.info("Match fields :")
                self.logger.info(match_field_string)
                self.logger.info(match_value_string)
            else:
                self.logger.info("Match fields : ALL MATCH")    # 匹配所有封包就直接印出來

            self.logger.info("")
            self.logger.info("Instructions fields : ")  # 取得執行動作
            for action in instructions:
                OFPInstructionActions = action.to_jsondict()[list(action.to_jsondict().keys())[0]]
                action_key = list(OFPInstructionActions.keys())[0]
                actions = OFPInstructionActions[action_key]
                
                self.logger.info(actions)   # 打印執行動作
        
        self.print_split_line("=",False)    # 結束分割線


    # 取得 port 的資訊
    def send_port_desc_stats_request(self, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
    
        # 取得 switch port 的 mac address
        request = ofp_parser.OFPPortDescStatsRequest(datapath, 0)   # 請求有關交換機 port 的詳細訊息
        datapath.send_msg(request)  # 發送一條 OFPPortDescStatsRequest ，透過 OFPPortDescStatsReply 取得 port 資訊
       
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
        self.logger.info(message)    # 顯示添加完成的 log

    # 添加匹配項目為 eth_src = [mac_address] 且有指定唯一輸出 port 的 flow entry
    def add_eth_src_flow_entry(self, mac_address, output_port, datapath):  
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match : eth_src = {} , actions : forwarding to port {}".format(datapath.id, mac_address, output_port)
        match = ofp_parser.OFPMatch(eth_src = mac_address)  # 以 eth_type =  ETH_TYPE_ARP, eth_src = [mac_address]為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 3, datapath, message)   # 優先級為 3
    
    # 添加匹配項目為 ipv4_src = [ipv4_address] 且有指定唯一輸出 port 的 flow entry
    def add_ipv4_src_flow_entry(self, ip_address, output_port, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match : eth_type=0x0800, ip_proto = 6, ipv4_src = {} , actions : forwarding to port {}".format(datapath.id, ip_address, output_port)
        match = ofp_parser.OFPMatch(eth_type=0x0800, ip_proto = 6, ipv4_src = ip_address)    # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address]為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 4, datapath, message)   # 優先級為 4
    
    # 添加匹配項目為 eth_src = [mac_address] 的 且有指定兩個輸出 port flow entry
    def add_eth_src_branch_flow_entry(self, mac_address, output_port_ein, output_port_zwei, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match : eth_src = {} , actions : forwarding to port1 {} , port2 {}".format(datapath.id, mac_address, output_port_ein, output_port_zwei)
        match = ofp_parser.OFPMatch(eth_src = mac_address)  # 以 eth_type =  ETH_TYPE_ARP, eth_src = [mac_address]為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port_ein),  # 輸出到兩個指定 port
                   ofp_parser.OFPActionOutput(port = output_port_zwei)]
        self.add_flow_entry(match, actions, 1, datapath, message)   # 優先級為 1

    # 添加匹配項目為 ipv4_src = [ipv4_address] 的 且有指定兩個輸出 port flow entry
    def add_ipv4_src_branch_flow_entry(self, ip_address, output_port_ein, output_port_zwei, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match : eth_type=0x0800, ip_proto = 6, ipv4_src = {} , actions : forwarding to port1 {} , port2 {}".format(datapath.id, ip_address, output_port_ein, output_port_zwei)
        match = ofp_parser.OFPMatch(eth_type=0x0800, ip_proto = 6, ipv4_src = ip_address)   # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address]為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port_ein),  # 輸出到兩個指定 port
                   ofp_parser.OFPActionOutput(port = output_port_zwei)]
        self.add_flow_entry(match, actions, 2, datapath, message)   # 優先級為 2

    # 添加匹配項目為 eth_src = [src_mac_address] eth_dst = [dst_mac_address] 且有指定唯一輸出 port 的 flow entry
    def add_eth_src_dst_flow_entry(self, src_mac_address, dst_mac_address, output_port, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match : eth_src = {} , eth_dst = {} , actions : forwarding to port {}".format(datapath.id, src_mac_address, dst_mac_address, output_port)
        match = ofp_parser.OFPMatch(eth_src = src_mac_address, eth_dst = dst_mac_address)    # 以 eth_type =  ETH_TYPE_ARP, eth_src = [src_mac_address] , eth_dst =[dst_mac_address] 為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 8, datapath, message)   # 優先級為 8

    # 添加匹配項目為 ipv4_src = [src_ip_address] ipv4_dst = [dst_ip_address] 且有指定唯一輸出 port 的 flow entry
    def add_ipv4_src_dst_flow_entry(self, src_ip_address, dst_ip_address, output_port, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match : eth_type=0x0800, ip_proto = 6, ipv4_src = {} , ipv4_dst = {} , actions : forwarding to port {}".format(datapath.id, src_ip_address, dst_ip_address, output_port)
        match = ofp_parser.OFPMatch(eth_type=0x0800, ip_proto = 6 , ipv4_src = src_ip_address, ipv4_dst = dst_ip_address)     # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address], ipv4_dst = [dst_ip_address] 為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 9, datapath, message)   # 優先級為 9

        # 添加指定 tcp_port = 5001 的 flow entry
        message = "Datapath {:2d} add flow entry with match : eth_type=0x0800, ip_proto = 6, ipv4_src = {} , ipv4_dst = {} tcp_dst = 5001 , actions : forwarding to port {}".format(datapath.id, src_ip_address, dst_ip_address, output_port)
        match = ofp_parser.OFPMatch(eth_type=0x0800, ip_proto = 6 , ipv4_src = src_ip_address, ipv4_dst = dst_ip_address, tcp_dst = 5001)   # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_src = [ip_address], ipv4_dst = [dst_ip_address], tcp_port = 5001 為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 10, datapath, message)   # 優先級為 10

    # 添加匹配項目為 eth_dst = [mac_address] 且有指定唯一輸出 port 的 flow entry
    def add_eth_dst_flow_entry(self, dst_mac_address, output_port, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match : eth_dst = {} , actions : forwarding to port {}".format(datapath.id, dst_mac_address, output_port)
        match = ofp_parser.OFPMatch(eth_dst = dst_mac_address)  # 以 eth_type =  ETH_TYPE_ARP, eth_src = [src_mac_address] , eth_dst =[dst_mac_address] 為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 5, datapath, message)   # 優先級為 5

    # 添加匹配項目為 ipv4_dst = [ip_address] 且有指定唯一輸出 port 的 flow entry
    def add_ipv4_dst_flow_entry(self, dst_ip_address, output_port, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        message = "Datapath {:2d} add flow entry with match :eth_type=0x0800, ip_proto = 6 , ipv4_dst = {} , actions : forwarding to port {}".format(datapath.id, dst_ip_address, output_port)
        match = ofp_parser.OFPMatch(eth_type=0x0800, ip_proto = 6 , ipv4_dst = dst_ip_address)   # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_dst = [dst_ip_address] 為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 6, datapath, message)   # 優先級為 6

        message = "Datapath {:2d} add flow entry with match : eth_type=0x0800, ip_proto = 6 , ipv4_dst = {} tcp_dst = 5001 , actions : forwarding to port {}".format(datapath.id, dst_ip_address, output_port)
        match = ofp_parser.OFPMatch(eth_type=0x0800, ip_proto = 6 , ipv4_dst = dst_ip_address, tcp_dst = 5001)  # 以 eth_type =  ETH_TYPE_IP, ip_proto = 6(TCP), ipv4_dst = [dst_ip_address], tcp_port = 5001 為匹配項目
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        self.add_flow_entry(match, actions, 7, datapath, message)   # 優先級為 7

    # 添加 meter entry 
    def add_meter_entry(self, meter_identifier, rate, datapath):
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        bandwidth = [ofp_parser.OFPMeterBandDrop(rate * 1000 , 10)]  # 帶寬 ： 超過 rate Mbps 的前 10 個封包進行丟棄
        meter_add_modification_message = ofp_parser.OFPMeterMod(    # meter mod 消息
            datapath = datapath,    # 交換機物件
            command = ofproto.OFPMC_ADD,    # 指是添加一個新的 meter entry
            flags = ofproto.OFPMF_KBPS, # 限速單位為 KBPS
            meter_id = meter_identifier,    # 指定 meter ID
            bands = bandwidth   # 帶寬
        )
        datapath.send_msg(meter_add_modification_message)   # 向交換機發送 meter mod message
        self.logger.info("Add meter entry with identifier {:2d} and bandwidth : {:4d} Mbps.".format(meter_identifier, rate))

    # 添加帶有 meter entry 的 flow entry
    def add_limited_rate_flow_entry(self, src_ip_address, dst_ip_address, output_port, meter_identifier, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息

        message = "Datapath {:2d} add flow entry with match :eth_type=0x0800, ip_proto = 17, ipv4_src = {} ipv4_dst = {} , actions : forwarding to port {} with meter entry : ID = {:2d}, bandwidth = {:4d} Mbps".format(datapath.id, src_ip_address, dst_ip_address, output_port, meter_identifier, (meter_identifier * 100))
        match = ofp_parser.OFPMatch(eth_type=0x0800, ip_proto = 17, ipv4_src = src_ip_address, ipv4_dst = dst_ip_address)   # 匹配項目為 eth_type = ETH_TYPE_IP, ip_proto = 17(UDP), ipv4_src = [src_ip_address], ipv4_dst = [dst_ip_address]
        actions = [ofp_parser.OFPActionOutput(port = output_port)]  # 輸出到指定 port
        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions), # 立即輸出到指定 port
                        ofp_parser.OFPInstructionMeter(meter_identifier, ofproto.OFPIT_METER)]   # 添加指定 meter entry
        
        flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message , 屬於Controller-to-switch Messages
                datapath = datapath,    # 交換機
                match = match,  # 匹配項目
                cookie = 0, # Cookie 為 0
                command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
                idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
                hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
                priority = 11,      # 優先級為 11 （目前最高匹配優先級）
                instructions = insturctions # 執行的動作
            )
        datapath.send_msg(flow_add_modification_message)    # 發送往交換機
        self.logger.info(message)    # 顯示添加完成的 log

        # 寫入 switches feature to orientation/controller/configuration/switch_features.csv
    
    def write_switch_features(self):
        self.clear_switch_features()

        switch_features_table_header = ["datapath_id","n_buffers","n_tables","auxiliary_id","capabilities"]   # 添加表標頭
        """
        datapath_id  : 交換機 identifier
        n_buffers    : 交換機上可用的封包緩衝區的數量
        n_tables     : 指定交換機支持的流表的最大數量
        auxiliary_id : 輔助連接的 id ，通常為 0 ，即主連接
        capabilities : OpenFlow 交換機支持的特性和功能
            要分析要轉成 8 位元二進位序列 (LSB--MSB)
            OFPC_FLOW_STATS = 1 << 0, /* Flow statistics. */
            OFPC_TABLE_STATS = 1 << 1, /* Table statistics. */
            OFPC_PORT_STATS = 1 << 2, /* Port statistics. */
            OFPC_GROUP_STATS = 1 << 3, /* Group statistics. */
            OFPC_IP_REASM = 1 << 5, /* Can reassemble IP fragments. */
            OFPC_QUEUE_STATS = 1 << 6, /* Queue statistics. */
            OFPC_PORT_BLOCKED = 1 << 8 /* Switch will block looping ports. */
        """
        with open(self.switch_features_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(switch_features_table_header)   # 寫入表標頭
            for feature in self.switch_features:    # 逐一寫入 switch_features
                writer.writerow(feature)    
            csv_file.close()
      
    # 將 switch_features.csv 進行初始化（清空交換機 features）
    def clear_switch_features(self):
        # 清空 switch_features.csv
        with open(self.switch_features_path, 'w') as csv_file:
            csv_file.write("")
            csv_file.close()

    # 顯示交換機 features 以及配置
    def show_switch_features_and_configuration(self,datapath):
        datapath_id=str(datapath.id)    # 交換機 ID

        feature = []    # 交換機 feature
        n_buffer = 0    # 可用的封包緩衝區的數量
        auxiliary_id = 0    # 輔助連接 ID
        
        for switch_feature in self.switch_features:
            if(str(switch_feature[0]) == datapath_id):
                feature = switch_feature
        if(feature[1] == 0):    # 交換機是否支持 buffer
            n_buffer = "NO_BUBBER"
        else:
            n_buffer = str(feature[1])
        if(feature[3] == 0):
            auxiliary_id = "MAIN_CONNECTION"
        else:
            auxiliary_id = str(feature[3])

        capabilities = feature[4] # 交換機支持的功能
        capabilities_binary_string = format(capabilities, '09b')    # 轉換為 9 位元二元序列

        OFPC_FLOW_STATS = "SUPPORTED" if bool(int(capabilities_binary_string[8])) else "NOT_SUPPORTED"  # 是否支持 flow 統計功能
        OFPC_TABLE_STATS = "SUPPORTED" if bool(int(capabilities_binary_string[7])) else "NOT_SUPPORTED"  # 是否支持 table 統計功能
        OFPC_PORT_STATS = "SUPPORTED" if bool(int(capabilities_binary_string[6])) else "NOT_SUPPORTED"  # 是否支持 port 統計功能
        OFPC_GROUP_STATS = "SUPPORTED" if bool(int(capabilities_binary_string[5])) else "NOT_SUPPORTED"  # 是否支持 group 統計功能
        OFPC_IP_REASM = "SUPPORTED" if bool(int(capabilities_binary_string[3])) else "NOT_SUPPORTED"  # 是否支持 IP 重組功能
        OFPC_QUEUE_STATS = "SUPPORTED" if bool(int(capabilities_binary_string[2])) else "NOT_SUPPORTED"  # 是否支持 Queue 統計功能
        OFPC_PORT_BLOCKED = "SUPPORTED" if bool(int(capabilities_binary_string[0])) else "NOT_SUPPORTED"  # 是否支持 PORT_BLOCKED

        self.print_split_line('-',True)
        print("Switch{:2s} with datapath_id {:2s}".format(datapath_id,datapath_id))
        print("n_buffer : {:10s} ,n_tables : {:3d} ,auxiliary_id : {:16s}".format(n_buffer,feature[2],auxiliary_id))
        print("capabilities : {:3d} = {:8s}".format(capabilities,capabilities_binary_string))
        print("OFPC_FLOW_STATS : {:15s}  OFPC_TABLE_STATS : {:15s}".format(OFPC_FLOW_STATS,OFPC_TABLE_STATS))
        print("OFPC_PORT_STATS : {:15s}  OFPC_GROUP_STATS : {:15s}".format(OFPC_PORT_STATS,OFPC_GROUP_STATS))
        print("OFPC_IP_REASM   : {:15s}  OFPC_QUEUE_STATS : {:15s}".format(OFPC_IP_REASM,OFPC_QUEUE_STATS))
        print("OFPC_PORT_BLOCKED   : {:15s}".format(OFPC_PORT_BLOCKED))
        self.print_split_line('-',False)

    # 打印出跟 terminal 同長度的分割線
    def print_split_line(self,char = '-',start = True):
        terminal_width = shutil.get_terminal_size().columns # 取得 terminal 長度
        split_line = char * terminal_width  # 分割線
        if(start):  # 起始分割線
            self.logger.info('\n'+split_line)
        else:   # 結束分割線
            self.logger.info(split_line)

        # 寫入 port 統計資訊到 port_statistic.json
    def write_port_statistic(self):
        self.clear_port_statistic() # 清空 ports_statistic.json
        
        with open(self.ports_statistic_path, 'w') as json_file:
            json.dump(self.ports_statistic, json_file)  # 寫入整個網路的交換機 port 統計資訊
            json_file.close()

    # 將 port_statistic.json 進行初始化（清空鏈路配置）
    def clear_port_statistic(self):
        # 清空 ports_statistic.json
        with open(self.ports_statistic_path, 'w') as json_file:
            json.dump({}, json_file)
            json_file.close()

    # 發送一條 OFPPortStatsRequest
    def send_port_stats_request(self, datapath):
        self.logger.info("Datapath{:2d} send an OFPPortStatsRequest".format(datapath.id))

        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        
        request = ofp_parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY) # 發送一條 OFPPortStatsRequest
        datapath.send_msg(request)
    
    # 發送一條 OFPFlowStatsRequest
    def send_flow_stats_request(self, datapath):
        self.logger.info("Datapath{:2d} send an OFPFlowStatsRequest".format(datapath.id))

        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
        
        request = ofp_parser.OFPFlowStatsRequest(datapath) # 發送一條 OFPFlowStatsRequest
        datapath.send_msg(request)

    def _request_stats(self,datapath):
        '''
        the function is to send requery to datapath
        '''
        self.logger.debug("send stats reques to datapath: %16x for port and flow info",datapath.id)
 
        ofproto = datapath.ofproto
        parser = datapath.ofproto_parser
 
        req = parser.OFPFlowStatsRequest(datapath)
        datapath.send_msg(req)
 
        req = parser.OFPPortStatsRequest(datapath, 0, ofproto.OFPP_ANY)
        datapath.send_msg(req)

    def show_port_statistic_information(self,datapath_id,port_number,contain_speed):
        port_statistic = self.ports_statistic[datapath_id][port_number]
        self.print_split_line("=",True)
        self.logger.info("Datapath {:2d} Port{:2d} Statics:".format(datapath_id,port_number))
        self.logger.info("port_no = {:2d}, hw_addr = {}, name = {:15s}".format(port_number,port_statistic['hw_addr'],port_statistic['name']))
        self.logger.info("")
        self.logger.info("config : {}".format(port_statistic['config']))
        self.logger.info("OFPPC_PORT_DOWN : {:16s}  OFPPC_NO_PACKET_IN : {:16s}".format(port_statistic['OFPPC_PORT_DOWN'],port_statistic['OFPPC_NO_PACKET_IN']))
        self.logger.info("OFPPC_NO_RECV   : {:16s}  OFPPC_NO_FWD       : {:16s}".format(port_statistic['OFPPC_NO_RECV'],port_statistic['OFPPC_NO_FWD']))
        self.logger.info("")
        self.logger.info("port_state      : {:16s}  ".format(port_statistic['port_state']))
        self.logger.info("curr            : {:16s}  supported          : {}".format(str(port_statistic['curr']),port_statistic['supported']))
        self.logger.info("peer            : {:16s}  advertised         : {}".format(str(port_statistic['peer']),port_statistic['advertised']))
        self.logger.info("")
        self.logger.info("OFPPF_10MB_HD   : {:16s}  OFPPF_100MB_HD     : {:16s}  OFPPF_1GB_HD : {}".format(port_statistic['OFPPF_10MB_HD'],port_statistic['OFPPF_100MB_HD'],port_statistic['OFPPF_1GB_HD']))
        self.logger.info("OFPPF_10MB_FD   : {:16s}  OFPPF_100MB_FD     : {:16s}  OFPPF_1GB_FD : {}".format(port_statistic['OFPPF_10MB_FD'],port_statistic['OFPPF_100MB_FD'],port_statistic['OFPPF_1GB_FD']))
        self.logger.info("max_speed       : {:12d} bps = {:12.2f} Mbps".format(int(port_statistic['max_speed']),(int(port_statistic['max_speed'])/1048576)))
        self.logger.info("curr_speed      : {:12d} bps = {:12.2f} Mbps".format(int(port_statistic['curr_speed']),(int(port_statistic['curr_speed'])/1048576)))
           
        self.print_split_line("-",True)
        self.logger.info("Last updated time : {:12.2f} second".format(port_statistic['update_time']))
        self.logger.info("rx_packets      : {:16d}  rx_bytes           : {:16d}  rx_errors : {}".format(port_statistic['rx_packets'],port_statistic['rx_bytes'],port_statistic['rx_errors']))
        self.logger.info("tx_packets      : {:16d}  tx_bytes           : {:16d}  tx_errors : {}".format(port_statistic['tx_packets'],port_statistic['tx_bytes'],port_statistic['tx_errors']))
        
        if(contain_speed):
            self.print_split_line("-",True)
            self.logger.info("free_bandwidth_rx     : {:12d} bps = {:12.2f} Mbps".format(int(port_statistic['free_bandwidth_rx']),(int(port_statistic['free_bandwidth_rx'])/1048576)))
            self.logger.info("free_bandwidth_tx     : {:12d} bps = {:12.2f} Mbps".format(int(port_statistic['free_bandwidth_tx']),(int(port_statistic['free_bandwidth_tx'])/1048576)))
            self.logger.info("occupied_bandwidth_rx : {:12d} bps = {:12.2f} Mbps".format(int(port_statistic['occupied_bandwidth_rx']),(int(port_statistic['occupied_bandwidth_tx'])/1048576)))
            self.logger.info("occupied_bandwidth_tx : {:12d} bps = {:12.2f} Mbps".format(int(port_statistic['occupied_bandwidth_tx']),(int(port_statistic['occupied_bandwidth_tx'])/1048576)))

        self.print_split_line("=",False)
        
    # 監控線程執行的函數，每 5 秒執行一次
    def every_five_second_monitoring(self):
        while(True):
            try:
                for datapath_id in self.datapaths:
                    self.send_port_desc_stats_request(self.datapaths[datapath_id])  # 取得 port 配置
                    self.send_flow_stats_request(self.datapaths[datapath_id])   # 取得 port 統計資訊
                    self.send_port_stats_request(self.datapaths[datapath_id])   # 取得 Flow entry 統計資訊
            except KeyError:
                self.logger.debug("Topology discovery happens KeyError")
            hub.sleep(5)    # 停止 5 秒