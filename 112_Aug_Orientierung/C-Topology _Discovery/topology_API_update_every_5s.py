from ryu.base import app_manager
from ryu.ofproto import ofproto_v1_3
from ryu.controller import ofp_event
from ryu.controller.handler import MAIN_DISPATCHER,CONFIG_DISPATCHER
from ryu.controller.handler import set_ev_cls

from ryu.topology.api import get_switch, get_link
import json
import csv
import shutil
from ryu.lib import hub
import time

class Topology_Discovery_by_API_update_five_seconds(app_manager.RyuApp):
    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    # 交換機啟動得初始化函數
    def __init__(self,*args,**kwargs):
        super(Topology_Discovery_by_API_update_five_seconds,self).__init__(*args,**kwargs)
        self.topology_api_app = self    # 引用 topology_api_app
        self.discover_thread = hub.spawn(self.every_five_second_monitoring)     # 建立一個 thread 用於每 5 秒的監控

        self.start_time = time.time()   # 紀錄啟動時間

        """
        整個網路的資料儲存點
        """
        self.datapaths = {} # 儲存整個網路的 Datapath 物件
        self.switches={}    # 儲存整個網路的 Switch 物件

        """
        配置文檔定義以及初始化
        """
        self.switch_features_path= './configuration/switch_features.csv'    # 交換機 feature 文檔路徑
        self.switch_features=[] # 整個網路的交換機 feature 
        self.clear_switch_features()    # 清空交換機 feature 文檔
        self.switch_connected_configuration_path = './configuration/switch_connected_configuration.json'    # 交換機配置文檔路徑
        self.switch_confguration = {}   # 整個網路的交換機配置
        self.clear_switch_confguration()    # 清空交換機配置文檔
        
        self.switches_link_path = './A-Topology _Discovery/configuration/switches_link.csv' # (optional) 鏈路的配置文檔路徑
        self.switches_link = [] # (optional) 鏈路的配置

        self.links= {}
        self.ports= {}

    """
    控制器事件響應
    1. switch_features_handler 響應 OFPT_FEATURES_REPLY
    2. get_config_reply_handler 響應 OFPT_GET_CONFIG_REPLY
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
        self.show_topology_api()    # 顯示拓樸
        self.logger.debug("Topology updates complete.".format(datapath.id))    # 顯示拓樸發現完成的 log
        
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
    
    """
    主動發送請求
    1. send_get_config_request 請求配置
    """

    # 發送 OFPT_GET_CONFIG_REQUEST = 7, /* Controller/switch message */
    def send_get_config_request(self, datapath):
        ofp_parser = datapath.ofproto_parser    # 創建和解析 OpenFlow message

        request = ofp_parser.OFPGetConfigRequest(datapath)  # 請求指定交換機的配置
        datapath.send_msg(request)  # 送去交換機

    """
    配置文檔寫入函數
    1. switch_features
    2. switch_confguration
    3. (optional) switches_link
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
            destination_input_port = self.links[str(destination_datapath) + "-" + str(source_datapath)]["port"]    # 目標的輸出端口
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

    """
    拓樸相關函數
    1. get_topology
    2. (optional) show_topology_api
    """

    # 更新拓樸配置的主要函數
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

    """
    特殊顯示函數
    1. show_switch_features_and_configuration 顯示交換機 features 以及配置
    2. print_split_line
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

    # 顯示拓樸
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

    # 監控線程執行的函數，每 5 秒執行一次
    def every_five_second_monitoring(self):
        while(True):
            try:
                self.get_topology()   # 更新拓樸變化
                self.show_topology_api()    # 顯示拓樸變化
            except KeyError:
                self.logger.debug("Topology discovery happens KeyError")
            hub.sleep(5)    # 停止 5 秒