from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls

class Flow_entries_management(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]   # 確定控制器所用OpenFlow版本

    # 交換機啟動得初始化函數
    def __init__(self, *args, **kwargs):
        super(Flow_entries_management, self).__init__(*args, **kwargs)

        self.host_mac_address = ["00:04:00:00:00:01", "00:04:00:00:00:02", "00:04:00:00:00:03", "00:04:00:00:00:04"]   # 主機的 mac address
        self.host_ip_address = ["10.0.0.10", "10.0.0.11", "10.0.0.12", "10.0.0.13"]    # 主機的 ip address

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
        self.logger.info("Datapath {0} add table-miss flow entry with actions: send entire package to controller.".format(datapath.id))    # 顯示添加完成的 log

        if(datapath.id < 5):    # 對於所有連接到主機的交換機 id < 5
            for index in range(len(self.host_mac_address)): # 遍歷所有主機的 mac address
                if(index == (datapath.id-1)):   # 如果是對應連接的主機
                    self.add_eth_src_flow_entry(self.host_mac_address[index], 2, datapath)    # 將封包發送到 port 2 (匹配 eth_src = [self.host_mac_address[index]])
                    self.add_ipv4_src_flow_entry(self.host_ip_address[index], 2, datapath)    # 將封包發送到 port 2 (匹配 ipv4_src = [self.host_ip_address[index]])
                else:   # 對於來源非連接主機
                    self.add_eth_src_flow_entry(self.host_mac_address[index], 1, datapath)    # 發送到連接主機
                    self.add_ipv4_src_flow_entry(self.host_ip_address[index], 1, datapath)    # 發送到連接主機

        """
        if(datapath.id == 1):
            self.add_src_flow_entry(self.host_mac_address[0], 2, datapath)    # 1 --> 5
            self.add_src_flow_entry(self.host_mac_address[1], 1, datapath)    # 1 --> host1
            self.add_src_flow_entry(self.host_mac_address[2], 1, datapath)    # 1 --> host1
            self.add_src_flow_entry(self.host_mac_address[3], 1, datapath)    # 1 --> host1
            
        if(datapath.id == 2):
            self.add_src_flow_entry(self.host_mac_address[0], 1, datapath)    # 2 --> host2
            self.add_src_flow_entry(self.host_mac_address[1], 2, datapath)    # 2 --> 5
            self.add_src_flow_entry(self.host_mac_address[2], 1, datapath)    # 2 --> host2
            self.add_src_flow_entry(self.host_mac_address[3], 1, datapath)    # 2 --> host2

        if(datapath.id == 3):
            self.add_src_flow_entry(self.host_mac_address[0], 1, datapath)    # 3 --> host3
            self.add_src_flow_entry(self.host_mac_address[1], 1, datapath)    # 3 --> host3
            self.add_src_flow_entry(self.host_mac_address[2], 2, datapath)    # 3 --> 7
            self.add_src_flow_entry(self.host_mac_address[3], 1, datapath)    # 3 --> host3

        if(datapath.id == 4):
            self.add_src_flow_entry(self.host_mac_address[0], 1, datapath)    # 4 --> host4
            self.add_src_flow_entry(self.host_mac_address[1], 1, datapath)    # 4 --> host4
            self.add_src_flow_entry(self.host_mac_address[2], 1, datapath)    # 4 --> host4
            self.add_src_flow_entry(self.host_mac_address[3], 2, datapath)    # 4 --> 7
        """
        
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

        """
        if(datapath.id == 5):
            self.add_src_branch_flow_entry(self.host_mac_address[0], 2, 3, datapath)   # 5 --> 2   5 --> 9
            self.add_src_branch_flow_entry(self.host_mac_address[1], 1, 3, datapath)   # 5 --> 1   5 --> 9
            self.add_src_branch_flow_entry(self.host_mac_address[2], 1, 2, datapath)   # 5 --> 1   5 --> 2
            self.add_src_branch_flow_entry(self.host_mac_address[3], 1, 2, datapath)   # 5 --> 1   5 --> 2

            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[1], 2, datapath)   # 5 --> 2
            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[2], 3, datapath)   # 5 --> 9
            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[3], 3, datapath)   # 5 --> 9

            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[0], 1, datapath)   # 5 --> 1
            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[2], 3, datapath)   # 5 --> 9
            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[3], 3, datapath)   # 5 --> 9

            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[0], 1, datapath)   # 5 --> 1
            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[1], 2, datapath)   # 5 --> 2

            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[0], 1, datapath)   # 5 --> 1
            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[1], 2, datapath)   # 5 --> 2

        if(datapath.id == 6):
            self.add_src_branch_flow_entry(self.host_mac_address[0], 2, 3, datapath)   # 6 --> 2   6 --> 10
            self.add_src_branch_flow_entry(self.host_mac_address[1], 1, 3, datapath)   # 6 --> 1   6 --> 10
            self.add_src_branch_flow_entry(self.host_mac_address[2], 1, 2, datapath)   # 6 --> 1   6 --> 2
            self.add_src_branch_flow_entry(self.host_mac_address[3], 1, 2, datapath)   # 6 --> 1   6 --> 2

            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[1], 2, datapath)   # 6 --> 2
            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[2], 3, datapath)   # 6 --> 10
            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[3], 3, datapath)   # 6 --> 10

            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[0], 1, datapath)   # 6 --> 1
            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[2], 3, datapath)   # 6 --> 10
            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[3], 3, datapath)   # 6 --> 10

            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[0], 1, datapath)   # 6 --> 1
            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[1], 2, datapath)   # 6 --> 2

            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[0], 1, datapath)   # 6 --> 1
            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[1], 2, datapath)   # 6 --> 2
        """

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

        """
        if(datapath.id == 7):
            self.add_src_branch_flow_entry(self.host_mac_address[0], 1, 2, datapath)   # 7 --> 3   7 --> 4
            self.add_src_branch_flow_entry(self.host_mac_address[1], 1, 2, datapath)   # 7 --> 3   7 --> 4
            self.add_src_branch_flow_entry(self.host_mac_address[2], 2, 3, datapath)   # 7 --> 4   7 --> 9
            self.add_src_branch_flow_entry(self.host_mac_address[3], 1, 3, datapath)   # 7 --> 3   7 --> 9

            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[2], 1, datapath)   # 7 --> 3
            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[3], 2, datapath)   # 7 --> 4

            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[2], 1, datapath)   # 7 --> 3
            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[3], 2, datapath)   # 7 --> 4

            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[0], 3, datapath)   # 7 --> 9
            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[1], 3, datapath)   # 7 --> 9
            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[3], 2, datapath)   # 7 --> 4

            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[0], 3, datapath)   # 7 --> 9
            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[1], 3, datapath)   # 7 --> 9
            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[2], 1, datapath)   # 7 --> 3

        if(datapath.id == 8):
            self.add_src_branch_flow_entry(self.host_mac_address[0], 1, 2, datapath)   # 8 --> 3   8 --> 4
            self.add_src_branch_flow_entry(self.host_mac_address[1], 1, 2, datapath)   # 8 --> 3   8 --> 4
            self.add_src_branch_flow_entry(self.host_mac_address[2], 2, 3, datapath)   # 8 --> 4   8 --> 10
            self.add_src_branch_flow_entry(self.host_mac_address[3], 1, 3, datapath)   # 8 --> 3   8 --> 10

            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[2], 1, datapath)   # 8 --> 3
            self.add_src_dst_flow_entry(self.host_mac_address[0], self.host_mac_address[3], 2, datapath)   # 8 --> 4

            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[2], 1, datapath)   # 8 --> 3
            self.add_src_dst_flow_entry(self.host_mac_address[1], self.host_mac_address[3], 2, datapath)   # 8 --> 4

            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[0], 3, datapath)   # 8 --> 10
            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[1], 3, datapath)   # 8 --> 10
            self.add_src_dst_flow_entry(self.host_mac_address[2], self.host_mac_address[3], 2, datapath)   # 8 --> 4

            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[0], 3, datapath)   # 8 --> 10
            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[1], 3, datapath)   # 8 --> 10
            self.add_src_dst_flow_entry(self.host_mac_address[3], self.host_mac_address[2], 1, datapath)   # 8 --> 3
        """

        # 對於頂層的交換機
        if(datapath.id > 8):
            message = "Datapath {:2d} add flow entry with match : in_port = {} , actions : forwarding to port {}".format(datapath.id, 1, 2)
            match = ofp_parser.OFPMatch(in_port = 1)
            actions = [ofp_parser.OFPActionOutput(port = 2)]
            self.add_flow_entry(match, actions, 1, datapath, message)   # 9 --> 7 / 10 --> 8

            message = "Datapath {:2d} add flow entry with match : in_port = {} , actions : forwarding to port {}".format(datapath.id, 2, 1)
            match = ofp_parser.OFPMatch(in_port = 2)
            actions = [ofp_parser.OFPActionOutput(port = 1)]    # 9 --> 5 / 10 --> 6
            self.add_flow_entry(match, actions, 1, datapath, message)

        # 對於 iperf udp 限速
        self.add_meter_entry(3, 300, datapath)    # 添加 meter entry 限速 300 Mbps

        # 對於交換機 1 
        if(datapath.id == 1):
            self.add_limited_rate_flow_entry(self.host_ip_address[0], self.host_ip_address[2], 2, 3, datapath)  # switch1 --> switch5 [300 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[0], 1, 3, datapath)  # switch1 --> host1   [300 Mbps]
        
        # 對於交換機 3
        if(datapath.id == 3):
            self.add_limited_rate_flow_entry(self.host_ip_address[0], self.host_ip_address[2], 1, 3, datapath)  # switch3 --> host3   [300 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[0], 2, 3, datapath)  # switch3 --> switch7 [300 Mbps]

        # 對於交換機 5
        if(datapath.id == 5):
            self.add_limited_rate_flow_entry(self.host_ip_address[0], self.host_ip_address[2], 3, 3, datapath)  # switch5 --> switch9 [300 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[0], 1, 3, datapath)  # switch5 --> switch1 [300 Mbps]

        # 對於交換機 7
        if(datapath.id == 7):
            self.add_limited_rate_flow_entry(self.host_ip_address[0], self.host_ip_address[2], 1, 3, datapath)  # switch7 --> switch3 [300 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[0], 3, 3, datapath)  # switch7 --> switch9 [300 Mbps]

        # 對於交換機 9
        if(datapath.id == 9):
            self.add_limited_rate_flow_entry(self.host_ip_address[0], self.host_ip_address[2], 2, 3, datapath)  # switch9 --> switch7 [300 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[0], 1, 3, datapath)  # switch9 --> switch5 [300 Mbps]

        # 對於 iperf udp 限速
        self.add_meter_entry(2, 200, datapath)    # 添加 meter entry 限速 200 Mbps
        # 對於交換機 3
        if(datapath.id == 3):
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[3], 3, 2, datapath)  # switch3 --> switch8 [200 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[3], self.host_ip_address[2], 1, 2, datapath)  # switch3 --> host3   [200 Mbps]

        # 對於交換機 4
        if(datapath.id == 4):
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[3], 1, 2, datapath)  # switch4 --> host4   [200 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[3], self.host_ip_address[2], 3, 2, datapath)  # switch4 --> switch8 [200 Mbps]
        
        # 對於交換機 8
        if(datapath.id == 8):
            self.add_limited_rate_flow_entry(self.host_ip_address[2], self.host_ip_address[3], 2, 2, datapath)  # switch8 --> switch4 [200 Mbps]
            self.add_limited_rate_flow_entry(self.host_ip_address[3], self.host_ip_address[2], 1, 2, datapath)  # switch8 --> switch3 [200 Mbps]

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