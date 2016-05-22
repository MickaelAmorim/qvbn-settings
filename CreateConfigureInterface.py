__author__ = 'Amorim'

import sys
import subprocess
import os
import json
import collections



def convert(data):
    if isinstance(data, basestring):
        return str(data)
    elif isinstance(data, collections.Mapping):
        return dict(map(convert, data.iteritems()))
    elif isinstance(data, collections.Iterable):
        return type(data)(map(convert, data))
    else:
        return data

def LanIdentifySubnet():
    DoubleQuotes='"'

    ReturnLanObjectSubnet=os.popen("qvbn-rpc -a txt -p '@children/*/@name="+DoubleQuotes+"overlay-subnet"+DoubleQuotes+"/@id' walk qvbn-guest-agent tid networking.subnet")
    LanObjectSubnet=ReturnLanObjectSubnet.read()
    ReturnLanObjectSubnet.close()

    return LanObjectSubnet

def WanIdentifySubnet():
    DoubleQuotes='"'

    ReturnWanObjectSubnet=os.popen("qvbn-rpc -a txt -p '@children/*/@name="+DoubleQuotes+"wan-network"+DoubleQuotes+"/@id' walk qvbn-guest-agent tid networking.network")
    WanObjectSubnet=ReturnWanObjectSubnet.read()
    ReturnWanObjectSubnet.close()

    return WanObjectSubnet

def ConfigureInterfaceBridge(overlayIntf, overlaySubnet, vlanIntf, wanSubnet, wanGateway, wan6, wan6Subnet, wan6Gateway, vcpeWanAllocation, hostNat, natIntf, vSwitch, vSwitchName, vSwitchOverlaySubnet, vSwitchVmSubnet, pathConf, pathScript):
    FlagLan=False
    FlagWan=False


    ReturnInterfaceBridge=os.popen("ifconfig | grep qvbn-g-br")
    InterfaceBridge=ReturnInterfaceBridge.read()
    InterfaceBridge=InterfaceBridge.rstrip()

    ReturnMatch=InterfaceBridge.find('qvbn-g-br')

    if ReturnMatch == -1 :
        print "Configuration Interface WAN/Overlay ... "
        IdLan=LanIdentifySubnet()
        if IdLan != "":
            print "Interface lan has already been configured."
            FlagLan = True

        IdWan=WanIdentifySubnet()
        if IdWan != "":
            print "Interface wan has already been configured."
            FlagWan = True

        if ((FlagLan and FlagWan ) or (FlagWan or FlagLan)) :
            print "Error qvbn-server : restart the system."
            os.popen("reboot")
            return 1

        if (FlagLan == False and FlagWan == False):
            #creation Json file configuration
            conf='''{"type":"vbn","server":"localhost:26265","overlay-name-prefix":"overlay","overlay-intf":"'''+overlayIntf+'''","overlay-subnet":"'''+overlaySubnet+'''","vlan-name-prefix":"vlan","vlan-intf":"'''+vlanIntf+'''","wan-name-prefix":"wan","wan-intf":"qvbn-g-br0000","wan-subnet":"'''+wanSubnet+'''","wan-gateway":"'''+wanGateway+'''","wan6":"'''+wan6+'''","wan6-subnet":"'''+wan6Subnet+'''","wan6-gateway":"'''+wan6Gateway+'''","vCPE-wan-allocation":"'''+vcpeWanAllocation+'''","host-nat":"'''+hostNat+'''","nat-intf":"'''+natIntf+'''","vSwitch":"'''+vSwitch+'''","vSwitch-name":"'''+vSwitchName+'''","vSwitch-overlay-subnet":"'''+vSwitchOverlaySubnet+'''","vSwitch-vm-subnet":"'''+vSwitchVmSubnet+'''"}'''
            try :
                file = open(pathConf+'/host.cfg', 'w+')
                file.write(conf)
                file.close()
            except :
                print ("Error configuration edit.")
                return 2

            try :
                cmd = "python "+pathScript+"/configure-vbn.py "+pathConf+"/host.cfg &"
                p = subprocess.Popen(cmd , shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                p.wait()
            except :
                print "Error script configure.sh."
                return 3

            print "Configuration has been finished."
    else :
        print "Interface bridge has already been configured."

    return

def init(config):
    # vBN server IPv4 setup

    # STEP 1 : ip_forward
    forward=os.popen("cat /proc/sys/net/ipv4/ip_forward")
    ResultForward = forward.read()
    forward.close()

    if (ResultForward == "0\n") :
        print("Configuration ip forward ... ")
        os.popen("echo '1' > /proc/sys/net/ipv4/ip_forward")

    if (ResultForward =="cat: /proc/sys/net/ipv4/ip_forward: No such file or directory" ) :
        print ("File 'ip_forward' not found.")

    if (ResultForward == "1\n") :
        print("Ip forward already set.")

    #STEP 2 : bridge interface ipv4 toward vCPE setup
    ConfigureInterfaceBridge(config['overlayIntf'], config['overlaySubnet'], config['vlanIntf'], config['wanSubnet'],
        config['wanGateway'], config['wan6'], config['wan6Subnet'], config['wan6Gateway'], config['vcpeWanAllocation'],
        config['hostNat'], config['natIntf'], config['vSwitch'], config['vSwitchName'], config['vSwitchOverlaySubnet'], config['vSwitchVmSubnet'],
        config['pathConf'], config['pathScript'])

    #STEP 3 : dhcp relay set
    os.popen("dhcrelay -4 -a -m forward "+config['dhcprelay'])


    return

def CreateLanPort(IpAddress, IdLanObjectSubnet, name, MacAddress):
    # qvbn-rpc set qvbn-guest-agent tid networking.port.gre remote_endpoint '{"ip_address":"192.168.20.21"}' local_subnet "751cfaf1-e963-4083-99ac-25be68eb5fd4" checksum_present false local_endpoint '{}' seq_num_present false mac_address "00:50:56:ad:c8:91" name "mamorim"

    DoubleQuotes='"'
    IpAddress="192.168.21.11"
    name="vCPE_2"
    MacAddress="00:50:56:ad:e1:68"

    ReturnLanObjectSubnetPort=os.popen("qvbn-rpc set qvbn-guest-agent tid networking.port.gre remote_endpoint '{"+DoubleQuotes+"ip_address"+DoubleQuotes+":"+DoubleQuotes+""+IpAddress+""+DoubleQuotes+"}' local_subnet "+IdLanObjectSubnet+" checksum_present false local_endpoint '{}' seq_num_present false mac_address "+DoubleQuotes+""+MacAddress+""+DoubleQuotes+" name "+DoubleQuotes+""+name+""+DoubleQuotes+" ")
    LanObjectSubnetPort=ReturnLanObjectSubnetPort.read()
    ReturnLanObjectSubnetPort.close()
    jsonDescriptionObject = json.loads(LanObjectSubnetPort)

    return jsonDescriptionObject['id']

def CreateWanPort(IdWanObjectSubnet):
    # qvbn-rpc set qvbn-guest-agent tid networking.port.tap network_id "fd516899-a6dd-456a-a921-439762a510c2"

    ReturnWanObjectSubnetPort=os.popen("qvbn-rpc set qvbn-guest-agent tid networking.port.tap network_id "+IdWanObjectSubnet+" ")
    WanObjectSubnetPort=ReturnWanObjectSubnetPort.read()
    jsonDescriptionObject = json.loads(WanObjectSubnetPort)
    ReturnWanObjectSubnetPort.close()

    return jsonDescriptionObject['id']

def RecoverLanObjectID(IdLanSubnet) :

    ReturnDescriptionObject=os.popen("qvbn-rpc -a pretty get qvbn-guest-agent tid networking.subnet id "+IdLanSubnet)
    DescriptionObject=ReturnDescriptionObject.read()
    ReturnDescriptionObject.close()
    jsonDescriptionObject = json.loads(DescriptionObject)

    #endvar=jsonDescriptionObject['allocation_pools']
    #print(endvar[0]['end'])

    return jsonDescriptionObject['id']

def RecoverWanObjectID(IdWanSubnet) :

    ReturnDescriptionObject=os.popen("qvbn-rpc -a pretty get qvbn-guest-agent tid networking.network id "+IdWanSubnet)
    DescriptionObject=ReturnDescriptionObject.read()
    ReturnDescriptionObject.close()
    jsonDescriptionObject = json.loads(DescriptionObject)
    #endvar=jsonDescriptionObject['allocation_pools']
    #print(endvar[0]['end'])

    return jsonDescriptionObject['id']

def IdentifyFavorObject() :
    DoubleQuotes='"'
    ReturnDescriptionObject=os.popen("qvbn-rpc -a txt -p '@children/*/@name="+DoubleQuotes+"Stock vCPE flavor - UML - OpenWRT (Attitude Adjustment)"+DoubleQuotes+"/@id' walk qvbn-guest-agent tid compute.flavor ")
    IdFlavorObject=ReturnDescriptionObject.read()
    ReturnDescriptionObject.close()

    IdFlavorObject = IdFlavorObject.replace("\n", "")

    return IdFlavorObject

def IdentifyKernelObject() :
    DoubleQuotes='"'
    ReturnDescriptionObject=os.popen("qvbn-rpc -a txt -p '@children/*/@name="+DoubleQuotes+"Stock vCPE kernel - UML - OpenWRT (Attitude Adjustment)"+DoubleQuotes+"/@id' walk qvbn-guest-agent tid storage.image")
    IdKernelObject=ReturnDescriptionObject.read()
    ReturnDescriptionObject.close()

    IdKernelObject = IdKernelObject.replace("\n", "")

    return IdKernelObject

def IdentifyRootfsObject() :
    DoubleQuotes='"'
    ReturnDescriptionObject=os.popen("qvbn-rpc -a txt -p '@children/*/@name="+DoubleQuotes+"Stock vCPE rootfs - UML - OpenWRT (Attitude Adjustment)"+DoubleQuotes+"/@id' walk qvbn-guest-agent tid storage.image ")
    IdRootfsObject=ReturnDescriptionObject.read()
    ReturnDescriptionObject.close()

    IdRootfsObject = IdRootfsObject.replace("\n", "")

    return IdRootfsObject

def CreateCowImageObject(IDRootfsObject) :
    ReturnDescriptionObject=os.popen("qvbn-rpc set qvbn-guest-agent tid storage.image format cow name vCPE dependencies '["+IDRootfsObject+"]'")
    DescriptionObject=ReturnDescriptionObject.read()
    jsonDescriptionObject = json.loads(DescriptionObject)
    ReturnDescriptionObject.close()

    return jsonDescriptionObject['id']

def CreateUmlContainer(IDKernelObject,IDCowImage) :
    ReturnDescriptionObject=os.popen("qvbn-rpc set qvbn-guest-agent tid storage.umlcontainer name vCPE kernel "+IDKernelObject+" rootfs "+IDCowImage+"")
    DescriptionObject=ReturnDescriptionObject.read()
    jsonDescriptionObject = json.loads(DescriptionObject)
    ReturnDescriptionObject.close()

    return jsonDescriptionObject['id']

def CreateUmlGuest(IDUmlContainer, IDFlavorObject, IDLanPort, IDWanPort) :
    ReturnDescriptionObject=os.popen("qvbn-rpc set qvbn-guest-agent tid compute.umlguest name vCPE image_container "+IDUmlContainer+" flavor "+IDFlavorObject+" eth1 "+IDLanPort+" eth0 "+IDWanPort+"")
    DescriptionObject=ReturnDescriptionObject.read()
    jsonDescriptionObject = json.loads(DescriptionObject)
    ReturnDescriptionObject.close()

    return jsonDescriptionObject['id']


def CreateComputerServer(IDUmlGuest) :
    DoubleQuotes='"'
    ReturnDescriptionObject=os.popen("qvbn-rpc set qvbn-guest-agent tid compute.server configuration '{"+DoubleQuotes+"tid"+DoubleQuotes+":"+DoubleQuotes+"compute.umlguest"+DoubleQuotes+","+DoubleQuotes+"id"+DoubleQuotes+":"+DoubleQuotes+IDUmlGuest+DoubleQuotes+"}' ")
    DescriptionObject=ReturnDescriptionObject.read()
    jsonDescriptionObject = json.loads(DescriptionObject)
    ReturnDescriptionObject.close()

    return jsonDescriptionObject['id']

def EnableConsoleConnection(IDUmlGuest):
    print("plop2")
    ReturnDescriptionObject=os.popen("qvbn-rpc set qvbn-guest-agent tid compute.umlguest id "+IDUmlGuest+" enable_console true ")
    print (ReturnDescriptionObject)
    print(ReturnDescriptionObject.read() )
    #ReturnDescriptionObject.close()
    print("plop3")
    ReturnDescriptionObject=os.popen("qvbn-rpc set "+IDUmlGuest+" tid console.pts enable true secure false")
    #print (ReturnDescriptionObject)
    #ReturnDescriptionObject.close()
    print("plop4")
    ReturnDescriptionObject=os.popen("qvbn-rpc -a pretty get "+IDUmlGuest+" tid console.pts")
    #print (ReturnDescriptionObject)
    DescriptionObject=ReturnDescriptionObject.read()
    jsonDescriptionObject = json.loads(DescriptionObject)
    #ReturnDescriptionObject.close()
    print("plop5")
    return jsonDescriptionObject

def vCPE_Instance() :

    # recover ID LAN subnet
    LanSubnet = LanIdentifySubnet()
    IDLanObject = RecoverLanObjectID(LanSubnet)

    # recover ID WAN subnet
    WanSubnet=WanIdentifySubnet()
    IDWanObject = RecoverWanObjectID(WanSubnet)

    # create Lan Port
    IDLanPort = CreateLanPort("192.168.21.10",IDLanObject, "vCPE_X","00:50:56:ad:e1:68")

    # create Wan Port
    IDWanPort = CreateWanPort(IDWanObject)

    # identify the flavor object
    IDFlavorObject = IdentifyFavorObject()

    # identify the kernel image object
    IDKernelObject = IdentifyKernelObject()

    # identify the rootfs image object
    IDRootfsObject = IdentifyRootfsObject()

    # create cow image object
    IDCowImage = CreateCowImageObject(IDRootfsObject)

    # create umlcontainer
    IDUmlContainer = CreateUmlContainer(IDKernelObject,IDCowImage)

    # create the umlguest
    IDUmlGuest = CreateUmlGuest(IDUmlContainer, IDFlavorObject, IDLanPort, IDWanPort)
    print "uml : "+IDUmlGuest
    # create a computer server object
    IDComputerServer = CreateComputerServer(IDUmlGuest)
    print " Computer server : "+IDComputerServer
    # enable vCPE console connection
    print("plop1")
    InfoConsole = EnableConsoleConnection(IDUmlGuest)
    print(InfoConsole)
    return

if __name__ == '__main__':
    config={}

    try :
        config['overlayIntf']=sys.argv[1]
        config['overlaySubnet']=sys.argv[2]
        config['vlanIntf']=sys.argv[3]
        config['wanSubnet']=sys.argv[4]
        config['wanGateway']=sys.argv[5]
        config['wan6']=sys.argv[6]
        config['wan6Subnet']=sys.argv[7]
        config['wan6Gateway']=sys.argv[8]
        config['vcpeWanAllocation']=sys.argv[9]
        config['hostNat']=sys.argv[10]
        config['natIntf']=sys.argv[11]
        config['vSwitch']=sys.argv[12]
        config['vSwitchName']=sys.argv[13]
        config['vSwitchOverlaySubnet']=sys.argv[14]
        config['vSwitchVmSubnet']=sys.argv[15]
        config['pathConf']=sys.argv[16]
        config['pathScript']=sys.argv[17]
        config['dhcprelay']=sys.argv[18]

    except :
        print "Error argument."
        print "Configuration is going to launch with defaults arguments."

        config['overlayIntf']="eth1"
        config['overlaySubnet']="192.168.21.0/24"
        config['vlanIntf']="eth0"
        config['wanSubnet']="192.168.20.0/24"
        config['wanGateway']="192.168.20.254"
        config['wan6']="enabled"
        config['wan6Subnet']="2001:420:4420:104::/64"
        config['wan6Gateway']="2001:420:4420:104::1"
        config['vcpeWanAllocation']="dhcp"
        config['hostNat']="disabled"
        config['natIntf']="eth3"
        config['vSwitch']="enabled"
        config['vSwitchName']="switch"
        config['vSwitchOverlaySubnet']="192.168.19.0/24"
        config['vSwitchVmSubnet']="192.168.18.0/24"
        config['pathConf']="/home/cisco/qvbn-api"
        config['pathScript']="/home/cisco/demo-setup"
        config['dhcprelay']="192.168.20.254"

    #try :
    #init(config)
    #except :
       #print "error configure."

    #try :
    vCPE_Instance()
    #except :
    #    print "Error set instance OpenWRT."