# -*- coding:utf-8 -*-
from mininet.cli import CLI
from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.node import Controller, OVSSwitch

if '__main__' == __name__:
	# 宣告 Mininet 使用的 Controller 種類
    network = Mininet(controller=RemoteController)
	
	# 指定 Controller 的 IP 及 Port，進行初始化
    ryu_controller = network.addController('ryu_controller',ip='127.0.0.1', port=6633)
	
    # Create network nodes: OpenFlow Switches and Hosts
    ListOpenFlowSwitch = [] # List of OpenFlow switches
    ListHost = [] # List of host

    # 加入 Switch
    for i in range(20):
        ListOpenFlowSwitch.append(network.addSwitch("switch%s"%str(i+1), cls = OVSSwitch)) #add ten OpenFlow virtual switches with type OVSSwitch and OVSSwitch_[index]
	
	# 加入主機，並指定 MAC，ip
    for i in range(4):
        ListHost.append(network.addHost("host%s"%str(i+1), ip = "10.0.0.%s/24"%str(i+10), mac = "00:04:00:00:00:%s"%str(i+1)))

	# 建立連線
    network.addLink(ListOpenFlowSwitch[0], ListHost[0], bw=1000,port1=1,port2=1)
    network.addLink(ListOpenFlowSwitch[1], ListHost[1], bw=1000,port1=1,port2=1)
    network.addLink(ListOpenFlowSwitch[2], ListHost[2], bw=1000,port1=1,port2=1)
    network.addLink(ListOpenFlowSwitch[3], ListHost[3], bw=1000,port1=1,port2=1)

    network.addLink(ListOpenFlowSwitch[0], ListOpenFlowSwitch[4], bw=1000,port1=2,port2=1)
    network.addLink(ListOpenFlowSwitch[1], ListOpenFlowSwitch[4], bw=1000,port1=2,port2=2)
    network.addLink(ListOpenFlowSwitch[0], ListOpenFlowSwitch[5], bw=1000,port1=3,port2=1)
    network.addLink(ListOpenFlowSwitch[1], ListOpenFlowSwitch[5], bw=1000,port1=3,port2=2)

    network.addLink(ListOpenFlowSwitch[2], ListOpenFlowSwitch[6], bw=1000,port1=2,port2=1)
    network.addLink(ListOpenFlowSwitch[3], ListOpenFlowSwitch[6], bw=1000,port1=2,port2=2)
    network.addLink(ListOpenFlowSwitch[2], ListOpenFlowSwitch[7], bw=1000,port1=3,port2=1)
    network.addLink(ListOpenFlowSwitch[3], ListOpenFlowSwitch[7], bw=1000,port1=3,port2=2)

    network.addLink(ListOpenFlowSwitch[4], ListOpenFlowSwitch[8], bw=1000,port1=3,port2=1)
    network.addLink(ListOpenFlowSwitch[6], ListOpenFlowSwitch[8], bw=1000,port1=3,port2=2)
    network.addLink(ListOpenFlowSwitch[5], ListOpenFlowSwitch[9], bw=1000,port1=3,port2=1)
    network.addLink(ListOpenFlowSwitch[7], ListOpenFlowSwitch[9], bw=1000,port1=3,port2=2)


    # 建立 Mininet
    network.build()

    # 啟動 Controller
    ryu_controller.start()
	
    # 啟動 Switch，並指定連結的 Controller 為 ryu_controller
    ListOpenFlowSwitch[0].start([ryu_controller])
    ListOpenFlowSwitch[1].start([ryu_controller])
    ListOpenFlowSwitch[2].start([ryu_controller])
    ListOpenFlowSwitch[3].start([ryu_controller])
    ListOpenFlowSwitch[4].start([ryu_controller])
    ListOpenFlowSwitch[5].start([ryu_controller])
    ListOpenFlowSwitch[6].start([ryu_controller])
    ListOpenFlowSwitch[7].start([ryu_controller])
    ListOpenFlowSwitch[8].start([ryu_controller])
    ListOpenFlowSwitch[9].start([ryu_controller])

    # 執行互動介面(mininet>...)
    CLI(network)
	# 互動介面停止後，則結束 Mininet
    network.stop()

    