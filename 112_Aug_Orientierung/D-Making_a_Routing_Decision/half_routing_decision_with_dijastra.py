from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER, CONFIG_DISPATCHER, DEAD_DISPATCHER
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
import heapq

class Forwarding_Brute_Force(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # 確定控制器所用OpenFlow版本

    # 交換機啟動得初始化函數
    def __init__(self,*args,**kwargs):
        super(Forwarding_Brute_Force,self).__init__(*args,**kwargs)
        self.topology_api_app = self    # 引用 topology_api_app
        self.discover_thread = hub.spawn(self.every_five_second_monitoring)     # 建立一個 thread 用於每 5 秒的監控

        self.start_time = time.time()   # 紀錄啟動時間

        """
        整個網路的資料儲存點
        """
        self.datapaths = {} # 儲存整個網路的 Datapath 物件
        self.switches = {}    # 儲存整個網路的 Switch 物件

        self.origin_lldp_links = [] # LLDP 封包呈現的原始鏈路

        """
        配置文檔定義以及初始化
        """
        self.switch_features_path = './configuration/switch_features.csv'    # 交換機 feature 文檔路徑
        self.switch_features = [] # 整個網路的交換機 feature 
        self.clear_switch_features()    # 清空交換機 feature 文檔
        self.switch_connected_configuration_path = './configuration/switch_connected_configuration.json'    # 交換機配置文檔路徑
        self.switch_confguration = {}   # 整個網路的交換機配置路徑
        self.clear_switch_confguration()    # 清空交換機配置文檔
        self.ports_statistic_path = './configuration/ports_statistic.json' # port 統計資訊的資料配置文檔路徑
        self.ports_statistic = {}   # 整個網路的交換機的 port 統計資訊
        self.clear_port_statistic() # 清空 port 統計資訊的配置文檔
        self.flow_statistic = []   # 整個網路的交換機的 flow 統計資訊
        
        # self.LLDP_links_path = './configuration/LLDP_links.csv' # LLDP 鏈路的配置文檔路徑
        # self.LLDP_links = []    # LLDP 鏈路
        # self.clear_LLDP_links()

        self.switches_link_path = './A-Topology _Discovery/configuration/switches_link.csv' # (optional) 鏈路的配置文檔路徑
        self.switches_link = [] # (optional) 鏈路的配置

        self.host_mac_address_mapped_datapath_id = {
            "00:04:00:00:00:01" : 1,
            "00:04:00:00:00:02" : 2,
            "00:04:00:00:00:03" : 3,
            "00:04:00:00:00:04" : 4,
        }

        self.links= {}
        self.ports= {}

    """
    控制器事件響應
    1. switch_features_handler 響應 OFPT_FEATURES_REPLY
    2. get_config_reply_handler 響應 OFPT_GET_CONFIG_REPLY
    3. port_desc_stats_reply_handler 響應 OFPPortDescStatsRequest
    3. packet_in_handler 響應 EventOFPPacketIn
    4. state_change_handler 響應 EventOFPStateChange
    5. add_flow_entry(副程式) 添加一個 flow entry
    """

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures,CONFIG_DISPATCHER)
    def switch_features_handler(self,event):
        # 取得資料 
        message = event.msg     # 事件的訊息
        datapath = message.datapath   # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message


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

        # 取得 switch features
        switch_features = [message.datapath_id,message.n_buffers,message.n_tables,message.auxiliary_id,message.capabilities] # 取得 features
        self.switch_features.append(switch_features)    # 添加 features 在 switch_features
        self.write_switch_features() # 寫入 switch_features.csv
        self.logger.debug("Datapath {0} write switch features complete.".format(datapath.id))    # 顯示寫入 features 完成的 log

        # 發送 OFPT_GET_CONFIG_REQUEST 取得交換機配置
        self.send_get_config_request(datapath)  # 發送 OFPT_GET_CONFIG_REQUEST 請求交換機配置

        self.datapaths.update( {str(datapath.id):datapath} )    # 此處添加交換機的（Datapath）物件配置

        self.get_topology() # 取得拓樸
        # self.show_topology_api()    # 顯示拓樸
        self.logger.debug("Topology updates complete.".format(datapath.id))    # 顯示拓樸發現完成的 log

        """
        當封包的協議類型為 LLDP 時，將封包轉發給 controller
        """
        # match = ofp_parser.OFPMatch()   # 匹配所有封包
        # actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER)]   # 將整個封包發送到控制器
        # insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
        # flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message ,屬於Controller-to-switch Messages
        #     datapath = datapath,    # 交換機
        #     match = match,  # 匹配項目
        #     cookie = 0, # Cookie 為 0
        #     command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
        #     idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
        #     hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
        #     priority = 1,   # 優先級為 1
        #     instructions = insturctions # 執行的動作
        # )
        # datapath.send_msg(flow_add_modification_message)    # 發送往交換機
        self.logger.debug("Datapath {0} add flow entry matched LLDP package with actions: send entire package to controller.".format(datapath.id))    # 顯示添加完成的 log

        # self.show_topology_lldp()   # 顯示拓樸 （LLDP）

        self.send_port_desc_stats_request(datapath) # 發送一個 send_port_desc_stats_request 給各個switch
        self.logger.debug("Datapath {0} send an OFPMP_PORT_STATS Request.".format(datapath.id))    # 顯示添加完成的 log
        # self.show_port_statistic()  # 顯示port 統計資訊

        self.send_flow_stats_request(datapath)  # 取得 flow 統計資訊
        # self.show_flow_statistic() # 顯示 flow 統計資訊

        """
        半學習 : 存在映射關係
        """

        # 添加存在最短路徑
        if(datapath.id <5):
            match = ofp_parser.OFPMatch(in_port=2,eth_type=0x0800)
            actions = [ofp_parser.OFPActionOutput(port=1)]
            self.add_flow_entry(datapath,match,actions,5)

            match = ofp_parser.OFPMatch(in_port=2,eth_type=0x0806)
            actions = [ofp_parser.OFPActionOutput(port=1)]
            self.add_flow_entry(datapath,match,actions,5)

            match = ofp_parser.OFPMatch(in_port=3,eth_type=0x0800)
            actions = [ofp_parser.OFPActionOutput(port=1)]
            self.add_flow_entry(datapath,match,actions,5)

            match = ofp_parser.OFPMatch(in_port=3,eth_type=0x0806)
            actions = [ofp_parser.OFPActionOutput(port=1)]
            self.add_flow_entry(datapath,match,actions,5)
        if(datapath.id > 8):
            match = ofp_parser.OFPMatch(in_port=2,eth_type=0x0800)
            actions = [ofp_parser.OFPActionOutput(port=1)]
            self.add_flow_entry(datapath,match,actions,5)

            match = ofp_parser.OFPMatch(in_port=2,eth_type=0x0806)
            actions = [ofp_parser.OFPActionOutput(port=1)]
            self.add_flow_entry(datapath,match,actions,5)

            match = ofp_parser.OFPMatch(in_port=1,eth_type=0x0800)
            actions = [ofp_parser.OFPActionOutput(port=2)]
            self.add_flow_entry(datapath,match,actions,5)

            match = ofp_parser.OFPMatch(in_port=1,eth_type=0x0806)
            actions = [ofp_parser.OFPActionOutput(port=2)]
            self.add_flow_entry(datapath,match,actions,5)

    # 響應 OFPT_GET_CONFIG_REQUEST 的 OFPT_GET_CONFIG_REPLY
    @set_ev_cls(ofp_event.EventOFPGetConfigReply, MAIN_DISPATCHER)
    def get_config_reply_handler(self, event):
        # 取得資料 
        message = event.msg # 事件的訊息
        datapath = message.datapath # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto   #  OpenFlow 協議相關訊息

        # 單一交換機配置的數據
        switch_datapath_configuration = {
            "datapath_id" : datapath.id,  # 交換機 ID
            "address" : datapath.address, # IPv4 地址 127.0.0.1 和 port number
            "is_active" : datapath.is_active, # 是否是活動的交換機
            "flag_value" : message.flags  # Handling of IP fragments.
        } 

        flag_enum = {   # enum ofp_config_flags
            ofproto.OFPC_FRAG_NORMAL : "OFPC_FRAG_NORMAL",  # 0 , 對 IP fragments 沒有特殊處理
            ofproto.OFPC_FRAG_NORMAL : "OFPC_FRAG_NORMAL",  # 1 << 0 , 丟棄 IP fragments
            ofproto.OFPC_FRAG_NORMAL : "OFPC_FRAG_NORMAL",  # 1 << 1 , 重新組裝 IP fragments
            ofproto.OFPC_FRAG_NORMAL : "OFPC_FRAG_NORMAL",  # 3
        }
        
        switch_datapath_configuration.update( {"flag_enum" : flag_enum} )   # 添加 flag 屬性
        switch_datapath_configuration.update( {"miss_send_len" : message.miss_send_len} )   # 發送到控制器的每個封包的字節數
        self.switch_confguration.update({str(datapath.id) : switch_datapath_configuration})   # 將該交換機的配置更新到整個網路的交換機配置
        self.write_switch_confguration()    # 將整個網路的交換機配置寫入 switch_connected_configuration.json

        # self.show_switch_features_and_configuration(datapath)   # 顯示交換機配置等等
        self.logger.debug("Datapath {0} write switch configuration complete.".format(datapath.id))
    
    # OFPPortDescStatsRequest 的響應，統計 port 的資訊
    @set_ev_cls(ofp_event.EventOFPPortDescStatsReply, MAIN_DISPATCHER)
    def port_desc_stats_reply_handler(self, event):
        # 取得訊息
        datapath = event.msg.datapath    # 數據平面的交換機（datapath）結構
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息
        # ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message
        
        ports = {}  # 交換機上的 port

        # 遍歷 event 中收到的每個 port 的統計訊息
        for statistic in event.msg.body:
            if statistic.port_no <= ofproto.OFPP_MAX:    # 如果 port_no(port number) 小於或等於 OFPP_MAX（最大的 port number ) -> 表示該 port 有效且不是 reserved port
                ports.update( {statistic.port_no : statistic.hw_addr} )   # 添加有效的 port 訊息  port number : MAC 地址
        self.ports_statistic.update({ datapath.id : ports} )    # 更新該交換機的 port 統計資訊
        self.write_port_statistic() # 將 port 統計資訊寫入文檔
        
        # 遍歷 ports 的每個 port, 並且為該 port 發送 LLDP 封包
        # for port_number in ports.keys():
        #     ingress_port = int(port_number)   # 輸入 port 為 port 的 port number
        #     match = ofp_parser.OFPMatch(eth_type = 34525 ,in_port = ingress_port) # 如果封包匹配 in_port = ingress_port 且 為 LLDP 類型

        #     for other_port_number in ports.keys():    # 遍歷其他非 ingress_port 的 port
        #         if(other_port_number != ingress_port):    # 如果是其他 port
        #             out_port = other_port_number    # 轉發 port 為 other_port
        #             self.send_lldp_packet(datapath,other_port_number,ports[other_port_number],10)  # 發送 LLDP 封包
        #             actions = [ofp_parser.OFPActionOutput(out_port),
        #                        ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,ofproto.OFPCML_NO_BUFFER)]    # 進行轉發封包的 action : 轉發到 output_port 以及控制器
        #             insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
        #             flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message ,屬於Controller-to-switch Messages
        #                 datapath = datapath,    # 交換機
        #                 match = match,  # 匹配項目
        #                 cookie = 0, # Cookie 為 0
        #                 command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
        #                 idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
        #                 hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
        #                 priority = 2,   # 優先級為 2，為了覆蓋掉預設的 LLDP 封包轉發動作
        #                 instructions = insturctions # 執行的動作
        #             )
        #             datapath.send_msg(flow_add_modification_message)    # 發送往交換機

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

        # 過濾協議為 LLDP 的封包
        if(package_ethernet.ethertype == ether_types.ETH_TYPE_LLDP):
            return 
            # self.logger.debug("A LLDP packet in from datapath {} ingress port = ".format(datapath, ingress_port))
            # package_LLDP = package.get_protocol(lldp.lldp)    # 取得 LLDP 封包
            # switch_source = "{:2d} : {:1d}".format(datapath_id,ingress_port)    # 來源交換機
            # try:    # 這邊不能用 lldp 指示的常數，會發生錯誤
            #     lldp_datapathid = package_LLDP.tlvs[0].chassis_id.decode()[5:]    
            #     lldp_datapathid = int(lldp_datapathid, 16)    # 目標交換機 ID
            #     lldp_ingress_port = package_LLDP.tlvs[1].port_id
            #     lldp_ingress_port = int.from_bytes(lldp_ingress_port, byteorder='big')      # 目標交換機的轉發 port 

            #     if(lldp_ingress_port <= ofproto.OFPP_MAX):  # 如果 port 是有效的
            #         switch_destination = "{:2d} : {:1d}".format(lldp_datapathid, lldp_ingress_port) # 目標交換機
            #         link = switch_source + ' <---> ' + switch_destination   # 原始 LLDP 鏈路
            #         if not any(link == search for search in self.origin_lldp_links): # 如果原始鏈路不存在於 origin_lldp_links
            #             self.origin_lldp_links.append(link)
            #             self.write_LLDP_links() # 寫入 LLDP 鏈路配置文檔
            # except ValueError:
            #     self.logger.debug("A LLDP packet happens ValueError in from datapath {} ingress port = ".format(datapath, ingress_port))
            #     return 

        if(package_ethernet.ethertype==2054):
            destination = package_ethernet.dst
            source = package_ethernet.src

            # 添加 Flooding flow entry
            match = ofp_parser.OFPMatch(eth_type=0x0800)   # 匹配 0x800
            actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),    # 將整個封包發送到控制器
                       ofp_parser.OFPActionOutput(port=ofproto.OFPP_FLOOD)]   # Flooding
            insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
            flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message ,屬於Controller-to-switch Messages
                datapath = datapath,    # 交換機
                match = match,  # 匹配項目
                cookie = 0, # Cookie 為 0
                command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
                idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
                hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
                priority = 1,   # 優先級為 1
                instructions = insturctions # 執行的動作
            )
            datapath.send_msg(flow_add_modification_message)    # 發送往交換機
            self.logger.debug("Datapath {0} add flood flow entry with actions: flooding and send entire package to controller.".format(datapath.id))    # 顯示添加完成的 log

            match = ofp_parser.OFPMatch(eth_type=0x0806)   # 匹配 0x800
            actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),    # 將整個封包發送到控制器
                    ofp_parser.OFPActionOutput(port=ofproto.OFPP_FLOOD)]   # Flooding
            insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
            flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message ,屬於Controller-to-switch Messages
                datapath = datapath,    # 交換機
                match = match,  # 匹配項目
                cookie = 0, # Cookie 為 0
                command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
                idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
                hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
                priority = 1,   # 優先級為 1
                instructions = insturctions # 執行的動作
            )
            datapath.send_msg(flow_add_modification_message)    # 發送往交換機
            self.logger.debug("Datapath {0} add flood flow entry with actions: flooding and send entire package to controller.".format(datapath.id))    # 顯示添加完成的 log

            self.add_flow_entry_priority_three(datapath)
            self.add_flow_entry_priority_four(datapath,source)
            
    # 響應有交換機與控制器斷開連接的狀態
    @set_ev_cls(ofp_event.EventOFPStateChange, [MAIN_DISPATCHER, DEAD_DISPATCHER])
    def state_change_handler(self, event):
        datapath = event.datapath   # 交換機
        if(event.state == DEAD_DISPATCHER):
            now_time = time.time()  # 取得現在時間
            elapsed_time = now_time - self.start_time   # 取得執行時間
            
            if(datapath != None):   # 如果交換機有效
                try:
                    self.logger.debug("Datapath {:2s} is disconnected in time {:.6f}.".format(str(datapath.id),elapsed_time))
                    self.datapaths.pop(datapath.id)    # 刪除斷開連接的 datapath
                except KeyError:    # 迴避初始配置
                    return
            
            # 更新拓樸配置 : API
            self.get_topology() # 取得拓樸
    
    # 響應 ofp_flow_stats_request ，回應 flow entry 的狀態
    @set_ev_cls(ofp_event.EventOFPFlowStatsReply, MAIN_DISPATCHER)
    def flow_stats_reply_handler(self, event):
        datapath = event.msg.datapath   # 交換機資訊
        flow_statstistic = event.msg.body # flow 統計資訊

        self.clear_flow_statistic(datapath.id)  # 清除交換機上的所有 flow entry

        for flow_entry in flow_statstistic:   # 遍歷 flow table
            table_id = flow_entry.table_id  # flow table ID
            duration_sec = flow_entry.duration_sec  # 存在時間（單位：秒）
            priority = flow_entry.priority  # 優先級
            idle_timeout = flow_entry.idle_timeout  # 未匹配過期時間
            hard_timeout = flow_entry.hard_timeout  # 存活過期時間
            flags = flow_entry.flags  # flow entry 屬性和特性
            cookie = flow_entry.cookie  # cookie
            packet_count = flow_entry.packet_count  # 匹配封包總數
            byte_count = flow_entry.byte_count  # 匹配封包位元總數
            match = flow_entry.match  # 匹配條件
            instructions = flow_entry.instructions  # 匹配執行動作
            length = flow_entry.length  # 長度
            
            flow_entry_data = [ # 一個 flow entry 的統計資訊
                datapath.id,
                table_id,
                duration_sec,
                priority,
                idle_timeout,
                hard_timeout,
                flags,
                cookie,
                packet_count,
                byte_count,
                match,
                instructions,
                length
            ]
            self.flow_statistic.append(flow_entry_data) # 加入 flow entry 的統計資訊到 flow_statistic
            # print(flow_entry_data)
    
    # 響應 EventOFPPortStatus，當交換機的 port 有所變化時
    @set_ev_cls(ofp_event.EventOFPPortStatus, MAIN_DISPATCHER)
    def port_status_handler(self, event):
        reason = event.msg.reason   # 事件的類型
        port = event.msg.desc.name.decode()   # 發生事件的 port
        datapath = event.msg.datapath   # 交換機
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息

        if(reason == ofproto.OFPPR_ADD):    # 新增一個 port
            self.logger.debug("Port: {:14s} is added.".format(port))
            print("Port: {:15s} is added.".format(port))
        elif(reason == ofproto.OFPPR_DELETE):  # 刪除一個 port
            self.logger.debug("Port: {:14s} is deleted.".format(port))
            print("Port: {:15s} is deleted.".format(port))
        elif(reason == ofproto.OFPPR_MODIFY):  # port 的狀態有所變化
            self.logger.debug("Port: {:14s} is modified.".format(port))
            print("Port: {:15s} is modified.".format(port))
        else:
            self.logger.debug("Port: {:14s} is change for unknown reason.".format(port))
            print("Port: {:15s} is change for unknown reason..".format(port))
    
    # 添加一個 flow entry
    def add_flow_entry(self,datapath,match,actions,priority):
        ofproto = datapath.ofproto  #  OpenFlow 協議相關訊息
        ofp_parser = ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        insturctions = [ofp_parser.OFPInstructionActions(ofproto.OFPIT_APPLY_ACTIONS, actions)] # 立即執行該動作
        flow_add_modification_message = ofp_parser.OFPFlowMod(  # 添加 flow entry message ,屬於Controller-to-switch Messages
            datapath = datapath,    # 交換機
            match = match,  # 匹配項目
            cookie = 0, # Cookie 為 0
            command = ofproto.OFPFC_ADD,    # 0, /* New flow. */ 標示消息類型為 OFPFC_ADD
            idle_timeout = 0,   # 不限制匹配過期時間 （永久存在）
            hard_timeout = 0,   # 不限制硬性過期時間 （永久存在）
            priority = priority,   # 優先級為 0 （ table-miss 的必要條件）
            instructions = insturctions # 執行的動作
        )
        datapath.send_msg(flow_add_modification_message)    # 發送往交換機

    """
    主動發送請求
    1. send_get_config_request 請求配置
    2. (optional) send_port_desc_stats_request 取得 port 的資訊
    3. (optional) send_lldp_packet 發送 LLDP 封包
    4. (optional) send_port_desc_stats_request_api 取得 port 的資訊
    3. send_flow_stats_request 取得 flow 統計資訊
    """

    # 發送 OFPT_GET_CONFIG_REQUEST = 7, /* Controller/switch message */
    def send_get_config_request(self, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        request = ofp_parser.OFPGetConfigRequest(datapath)  # 請求指定交換機的配置
        datapath.send_msg(request)  # 送去交換機

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
        tlvs = (chassis_id,port_id,ttl,end) # tlvs = 設備 ID, port ID ,time-to-live ,end
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

    # 取得 port 的資訊
    def send_port_desc_stats_request_api(self):
        for key in self.datapaths.keys():   # 遍歷交換機物件
            datapath = self.datapaths[key]  # 交換機物件
            ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

            # 取得 switch port 的 mac address
            request = ofp_parser.OFPPortDescStatsRequest(datapath, 0)   # 請求有關交換機 port 的詳細訊息
            datapath.send_msg(request)  # 發送一條 OFPPortDescStatsRequest ，透過 OFPPortDescStatsReply 取得 port 資訊

    # 取得 flow 統計資訊
    def send_flow_stats_request(self, datapath):
        parser = datapath.ofproto_parser
        
        request = parser.OFPFlowStatsRequest(datapath)  # 發送 ofp_flow_stats_request
        datapath.send_msg(request)

    """
    配置文檔寫入函數
    1. switch_features
    2. switch_confguration
    3. (optional) switches_link
    4. port_statistic
    5. (optional) LLDP_links
    6. flow_statitic (clear only) 並且不是清除文檔
    """

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

    # 寫入交換機配置到 orientation/controller/configuration/switch_connected_configuration.json
    def write_switch_confguration(self):
        self.clear_switch_confguration()    # 清空交換機配置
        with open(self.switch_connected_configuration_path, 'w') as json_file:
            json.dump(self.switch_confguration, json_file)  # 寫入整個網路的交換機配置
            json_file.close()
    
    # 將 switch_connected_configuration.json 進行初始化（清空交換機配置）
    def clear_switch_confguration(self):
        # 清空 switch_connected_configuration.json
        with open(self.switch_connected_configuration_path, 'w') as json_file:
            json.dump({}, json_file)
            json_file.close()

    # 寫入交換機配置到 orientation/controller/A-Topology _Discovery/configuration/switches_link.csv
    def write_switches_link(self):
        # 清空 switches_link.csv 
        self.clear_switches_link()

        switches_link_data_rable_header = ["source_datapath","source_output_port","destination_datapath","destination_input_port"]  # switches_link.csv 的標頭
        switches_link_data = []   # 準備寫入的資料

        links_keys = self.links.keys()
        for key in links_keys:  # 遍歷 self.switches_link
            link = self.links[key]  # 取得鏈路
            source_datapath = link["source_datapath"]   # 來源的 datapath_id
            destination_datapath = link["destination_datapath"] # 目標的 datapath_id
            source_output_port = link["port"]   # 來源的輸出端口
            try:
                destination_input_port = self.links[str(destination_datapath) + "-" + str(source_datapath)]["port"]    # 目標的輸出端口
            except KeyError:    # 迴避初始化發生的錯誤
                self.logger.debug("KeyError happens when write_switches_link find "+str(destination_datapath) + "-" + str(source_datapath))
                destination_input_port = 1
            append_data=[source_datapath,source_output_port,destination_datapath,destination_input_port]    # 要加入的資料
            switches_link_data.append(append_data)

        with open(self.switches_link_path, 'w') as csv_file:
            writer = csv.writer(csv_file)
            writer.writerow(switches_link_data_rable_header)   # 寫入表標頭
            for link_data in switches_link_data:    # 逐一寫入鏈路資料
                writer.writerow(link_data)    
            csv_file.close()
        
    # 將 switches_link.csv 進行初始化（清空鏈路配置）
    def clear_switches_link(self):
        # 清空 switches_link.csv
        with open(self.switches_link_path, 'w') as csv_file:
            csv_file.write("")
            csv_file.close()

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
    
    # 寫入 LLDP 鏈路配置到 orientation/controller/configuration/LLDP_links.csv
    def write_LLDP_links(self):
        # 清空 LLDP_links.csv 
        self.clear_LLDP_links()

        # 配置文檔標頭
        LLDP_links_table_header = ["switch_source_name","switch_source_datapath_id","switch_source_portName","switch_source_portNumber","switch_source_port_mac_address","switch_destination_name","switch_destination_datapath_id","switch_destination_portName","switch_destination_portNumber","switch_destination_port_mac_address"]
        
        # 原始資料處理
        for origin_link in self.origin_lldp_links:
            try:
                source = origin_link.split(' <---> ')[0]    # 來源交換機
                destination = origin_link.split(' <---> ')[1]   # 目標交換機 ID

                source_ID = int(source.split(' : ')[0])  # 來源交換機 ID
                source_name = "switch{:2d}".format(source_ID)   # 來源交換機名稱
                source_ingress_port = int(source.split(' : ')[1]) # 來源交換機 ingress port
                source_port_name = "port{}".format(source_ingress_port)
                source_mac_address = self.ports_statistic[source_ID][source_ingress_port]   # 來源交換機 ingress port 的 mac address

                destination_ID = int(destination.split(' : ')[0])  # 目標交換機 ID
                destination_name = "switch{:2d}".format(destination_ID)   # 來源交換機名稱
                destination_ingress_port = int(destination.split(' : ')[1]) # 目標交換機 ingress port
                destination_port_name = "port{}".format(destination_ingress_port)
                destination_mac_address = self.ports_statistic[destination_ID][destination_ingress_port]   # 目標交換機 ingress port 的 mac address

                self.LLDP_links.append([    # 更新 LLPD_links
                    source_name, source_ID, source_port_name, source_ingress_port, source_mac_address,
                    destination_name, destination_ID, destination_port_name, destination_ingress_port, destination_mac_address
                ])

            except KeyError:    # 避免初始配置產生衝突
                self.logger.debug("LLDP topology configuration happens KeyError")
                return 
            
        with open(self.LLDP_links_path, 'w') as csv_file:   # 寫入文檔
            writer = csv.writer(csv_file)   
            writer.writerow(LLDP_links_table_header)   # 寫入表標頭
            
            unique_ordered_dict = OrderedDict.fromkeys(tuple(sublist) for sublist in self.LLDP_links)   # 去除重複鏈路
            self.LLDP_links = [list(sublist) for sublist in unique_ordered_dict.keys()] 

            for link_data in self.LLDP_links:    # 逐一寫入鏈路資料
                writer.writerow(link_data)    
            csv_file.close()
        
    # 將 LLDP_links.csv 進行初始化（清空鏈路配置）
    def clear_LLDP_links(self):
        # 清空 LLDP_links.csv
        with open(self.LLDP_links_path, 'w') as csv_file:
            csv_file.write("")
            csv_file.close()

    # 將指定交換機所有的 flow entry 刪除
    def clear_flow_statistic(self,datapath_id):
        for index,flow in enumerate(self.flow_statistic):    # 遍歷 self.flow_statistic
            if(flow[0] == datapath_id): # 如果是指定交換機上的 flow entry
                self.flow_statistic.pop(index)  # 刪除該 flow entry

    """
    拓樸相關函數
    1. get_topology
    2. get_topology_lldp
    """

    # 更新拓樸配置的主要函數（API）
    def get_topology(self):
        # 更新交換機列表
        switch_list = get_switch(self.topology_api_app) # 取得交換機物件列表（Type : Switch ）
        for switch in switch_list:
            self.switches.update({str(switch.dp.id):switch}) # 以 {id : Switch 物件} 的形式更新 self.switches

        # 更新鏈路列表
        link_list = get_link(self.topology_api_app) # 取得鏈路物件列表（Type : Link ）
        for link in link_list: 
            index = str(link.src.dpid) + "-" + str(link.dst.dpid) # 將 index 設置為 [來源的 datapath_id]-[目標的 datapath_id]
            append_data={   # 要更新的資料
                "source_datapath":link.src.dpid,    # 來源的 datapath_id
                "destination_datapath":link.dst.dpid,   # 目標的 datapath_id
                "port":link.src.port_no # 來源要轉發到目標的 outpur port number
            }
            self.links.update({index:append_data})  # 更新 self.links

        self.write_switches_link() # 寫入配置文檔

    # 更新拓樸配置的主要函數（LLDP）
    def get_topology_lldp(self):
        for key in self.datapaths.keys():   # 遍歷交換機物件
            self.send_port_desc_stats_request(self.datapaths[key])  # 發送 FPPortDescStatsRequest 使 FPPortDescStatsReply 統計 port 資訊以及產生 LLDP 封包
    
    """
    特殊顯示函數
    1. show_switch_features_and_configuration 顯示交換機 features 以及配置
    2. print_split_line
    3. (optional) show_topology_api
    4. (optional) show_topology_lldp
    5. show_port_statistic 顯示 port 統計資訊
    6. show_flow_statistic 顯示 flow 統計資訊
    """

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

        config = self.switch_confguration[datapath_id]  # 取得交換機配置
        address = config["address"][0]  # 本機地址
        port = config["address"][1] # 連接到本機地址的 port
        is_active = "ACTIVE" if config["is_active"] else "INACTIVE" # 交換機活動狀態
        flag = config["flag_enum"][config["flag_value"]]    # IP 重組的功能
        miss_send_len = config["miss_send_len"] # table-miss 時發送回控制器進行處理的數據量的限制

        self.print_split_line('-',True)
        print("Switch{:2s} with datapath_id {:2s}".format(datapath_id,datapath_id))
        print("n_buffer : {:10s} ,n_tables : {:3d} ,auxiliary_id : {:16s}".format(n_buffer,feature[2],auxiliary_id))
        print("capabilities : {:3d} = {:8s}".format(capabilities,capabilities_binary_string))
        print("OFPC_FLOW_STATS : {:15s}  OFPC_TABLE_STATS : {:15s}".format(OFPC_FLOW_STATS,OFPC_TABLE_STATS))
        print("OFPC_PORT_STATS : {:15s}  OFPC_GROUP_STATS : {:15s}".format(OFPC_PORT_STATS,OFPC_GROUP_STATS))
        print("OFPC_IP_REASM   : {:15s}  OFPC_QUEUE_STATS : {:15s}".format(OFPC_IP_REASM,OFPC_QUEUE_STATS))
        print("OFPC_PORT_BLOCKED   : {:15s}".format(OFPC_PORT_BLOCKED))
        print("address : {:10s} with port : {:5d}".format(address,port))
        print("is_active : {:8s} ,flag : {:16s} ,miss_send_len : {:3d}".format(is_active,flag,miss_send_len))
        self.print_split_line('-',False)

    # 打印出跟 terminal 同長度的分割線
    def print_split_line(self,char = '-',start = True):
        terminal_width = shutil.get_terminal_size().columns # 取得 terminal 長度
        split_line = char * terminal_width  # 分割線
        if(start):  # 起始分割線
            print('\n'+split_line)
        else:   # 結束分割線
            print(split_line)

    # 顯示拓樸 (topology api)
    def show_topology_api(self):
        self.print_split_line('-',True)
        now_time = time.time()  # 取得現在時間
        elapsed_time = now_time - self.start_time   # 取得執行時間

        print("Topology of network with elapsed time: {:.6f}".format(elapsed_time))
        with open(self.switches_link_path, 'r') as csvfile: # 讀取 switches_link.csv
            csvreader = csv.DictReader(csvfile)
            for link in list(csvreader)[1:]:  # 遍歷鏈路，除了標頭
                print("switch{:2s} : {} connects to switch{:2s} : {}".format(str(link["source_datapath"]),link["source_output_port"],str(link["destination_datapath"]),link["destination_input_port"]))
            csvfile.close()
        self.print_split_line('-',False)

    # 顯示拓樸 (topology lldp)
    def show_topology_lldp(self):
        self.print_split_line('-',True)
        now_time = time.time()  # 取得現在時間
        elapsed_time = now_time - self.start_time   # 取得執行時間

        print("Topology of network with elapsed time: {:.6f}".format(elapsed_time))
        with open(self.LLDP_links_path, 'r') as csvfile: # 讀取 switches_link.csv
            csvreader = csv.DictReader(csvfile)
            for link in list(csvreader)[1:]:  # 遍歷鏈路，除了標頭
                print("{:7s} : {:2s} [{}] connects to {:7s} : {:2s} [{}]".format(link["switch_source_name"],link["switch_source_portNumber"],link["switch_source_port_mac_address"],link["switch_destination_name"],link["switch_destination_portNumber"],link["switch_destination_port_mac_address"]))
            csvfile.close()
        self.print_split_line('-',False)

    # 輸出 port 統計資訊
    def show_port_statistic(self):
        self.print_split_line('-',True)
        now_time = time.time()  # 取得現在時間
        elapsed_time = now_time - self.start_time   # 取得執行時間

        print("Ports statistics of network with elapsed time: {:.6f}".format(elapsed_time))
        with open(self.ports_statistic_path, 'r') as json_file: # 讀取 port_statistic.json
            json_data = json_file.read()    # 讀取資訊，此時為字串
            port_statistic_data =  json.loads(json_data)    # 轉換為 dictionary

            try:
                for datapath_id in port_statistic_data.keys():
                    message = "switch{:2s} : ".format(datapath_id)  # 交換機資訊
                    for port_number in port_statistic_data[datapath_id]:
                        message += "port{} : [{}]  ".format(port_number,port_statistic_data[datapath_id][port_number])    # port number 與 mac address 的映射
                    print(message)  # 輸出端口資訊
            except KeyError:
                self.logger.debug("KeyError happens when show_port_statistic")
                return
            json_file.close()
        self.print_split_line('-',False)

    # 輸出 port 統計資訊
    def show_flow_statistic(self):
        datapath_ids = self.datapaths.keys()    # 取得 datapath id的陣列
        datapath_ids = [int(datapath_id) for datapath_id in datapath_ids]

        now_time = time.time()  # 取得現在時間
        elapsed_time = now_time - self.start_time   # 取得執行時間

        for flow in self.flow_statistic:    # 遍歷 flow_statistic
            print("Flow entries in switch{:2d} with elapsed time: {:.6f}".format(flow[0],elapsed_time))
            print("table_id = {:6d} duration(sec) = {:6d} priority = {:6d}".format(flow[1],flow[2],flow[3]))
            print("idle_timeout = {:6d} hard_timeout = {:6d} flags = {:6d}".format(flow[4],flow[5],flow[6]))
            print("cookie = {:6d} length = {:6d}".format(flow[7],flow[-1]))
            print("packet_count = {:15d} byte_count = {:14d} ".format(flow[8],flow[9]))
            print("mathch = " + str(flow[10]))
            print("instructions = " + str(flow[11]))

   

    # def find_next_forwarding_node(self,)
    """
    Dijkstra's Algorithm 
    1. get_graph_for_dijkstra
    2. 
    """
    # 取得合適的圖
    def get_graph_for_dijkstra(self):
        graph = {}  # 創見空圖
        for datapath_id in self.datapaths.keys():   # 取得所有 datapath 的 ID
            graph.update( {str(datapath_id) : {} } )    # 初始畫圖

        with open(self.switches_link_path, 'r') as csv_file:
            csvreader = csv.DictReader(csv_file)    # 讀取鏈接配置
            for row in list(csvreader)[1:]:  # 遍歷鏈路，除了標頭
                source_datapath = str(row["source_datapath"])
                destination_datapath = str(row["destination_datapath"])

                graph[source_datapath].update( {destination_datapath : 1} ) # 更新圖
            csv_file.close()
        return graph

    # 透過 Dijkstra 尋找最短路徑
    def find_shortest_path_dijkstra(self,start,end):
        graph = self.get_graph_for_dijkstra()   
        
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

        # Backtrack from the end node to the start node to retrieve the path
        path = []
        current_node = end
        while current_node is not None:
            path.insert(0, current_node)
            current_node = previous_node[current_node]

        return path

    # 建立對應表相
    def add_flow_entry_priority_three(self,datapath):
        datapath_id = datapath.id
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        for mac in self.host_mac_address_mapped_datapath_id.keys():
            if(int(self.host_mac_address_mapped_datapath_id[mac]) == datapath_id ):
                match = ofp_parser.OFPMatch(eth_type=0x0806, eth_dst = mac)
                actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),    # 將整個封包發送到控制器
                   ofp_parser.OFPActionOutput(port=1)]
                self.add_flow_entry(datapath,match,actions,3)
                match = ofp_parser.OFPMatch(eth_type=0x0800, eth_dst = mac)
                actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),    # 將整個封包發送到控制器
                   ofp_parser.OFPActionOutput(port=1)]
                self.add_flow_entry(datapath,match,actions,3)
            else:
                next_node = self.find_shortest_path_dijkstra(str(datapath.id),str(self.host_mac_address_mapped_datapath_id[mac]))[1]
                out_put_port = self.find_port_by_nodes(str(datapath.id),str(next_node))

                match = ofp_parser.OFPMatch(eth_type=0x0806, eth_dst = mac)
                actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),    # 將整個封包發送到控制器
                   ofp_parser.OFPActionOutput(port=out_put_port)]
                self.add_flow_entry(datapath,match,actions,3)

                match = ofp_parser.OFPMatch(eth_type=0x0800, eth_dst = mac)
                actions = [ofp_parser.OFPActionOutput(ofproto.OFPP_CONTROLLER, ofproto.OFPCML_NO_BUFFER),    # 將整個封包發送到控制器
                   ofp_parser.OFPActionOutput(port=out_put_port)]
                self.add_flow_entry(datapath,match,actions,3)
    
    def add_flow_entry_priority_four(self,datapath,source_mac):
        datapath_id = datapath.id
        ofproto = datapath.ofproto    # OpenFlow 協議相關訊息
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        for mac in self.host_mac_address_mapped_datapath_id.keys():
            if(mac != source_mac):
                if(int(self.host_mac_address_mapped_datapath_id[mac]) == datapath_id ):
                    match = ofp_parser.OFPMatch(eth_type=0x0806,eth_src = source_mac, eth_dst = mac)
                    actions = [ofp_parser.OFPActionOutput(port=1)]
                    self.add_flow_entry(datapath,match,actions,4)
                    match = ofp_parser.OFPMatch(eth_type=0x0800,eth_src = source_mac, eth_dst = mac)
                    actions = [ofp_parser.OFPActionOutput(port=1)]
                    self.add_flow_entry(datapath,match,actions,4)
                else:
                    next_node = self.find_shortest_path_dijkstra(str(datapath.id),str(self.host_mac_address_mapped_datapath_id[mac]))[1]
                    out_put_port = self.find_port_by_nodes(str(datapath.id),str(next_node))

                    match = ofp_parser.OFPMatch(eth_type=0x0806, eth_src = source_mac,eth_dst = mac)
                    actions = [ofp_parser.OFPActionOutput(port=out_put_port)]
                    self.add_flow_entry(datapath,match,actions,4)

                    match = ofp_parser.OFPMatch(eth_type=0x0800, eth_src = source_mac,eth_dst = mac)
                    actions = [ofp_parser.OFPActionOutput(port=out_put_port)]
                    self.add_flow_entry(datapath,match,actions,4)

                
    def find_port_by_nodes(self,start,next):
        with open(self.switches_link_path, 'r') as csv_file:
            csvreader = csv.DictReader(csv_file)    # 讀取鏈接配置
            for row in list(csvreader)[1:]:  # 遍歷鏈路，除了標頭
                source_datapath = str(row["source_datapath"])
                destination_datapath = str(row["destination_datapath"])

                if(source_datapath == start and destination_datapath == next):
                    return int(row["source_output_port"])
            csv_file.close()

    # 監控線程執行的函數，每 5 秒執行一次
    def every_five_second_monitoring(self):
        while(True):
            try:
                # self.get_topology_lldp()    # 更新拓樸變化（LLDP）+ 更新 port 統計資訊
                # self.show_topology_lldp()   # 顯示拓樸變化

                self.get_topology()   # 更新拓樸變化（API）
                # self.show_topology_api()    # 顯示拓樸變化

                self.send_port_desc_stats_request_api() # 更新 port 統計資訊
                # self.show_port_statistic()  # 顯示 port 統計資訊
                for datapath_id in self.datapaths.keys():   # 發送 flow_stats_request
                    self.send_flow_stats_request(self.datapaths[datapath_id])
                # self.show_flow_statistic()  # 顯示 flow 統計資訊
                
            except KeyError:
                self.logger.debug("Topology discovery happens KeyError")
            hub.sleep(5)    # 停止 5 秒