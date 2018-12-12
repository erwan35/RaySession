from liblo import Server, Address
import argparse
import liblo, socket
import sys, os, shlex, subprocess
from PyQt5.QtCore import QLocale, QTranslator, QT_VERSION_STR, QFile
from PyQt5.QtGui  import QIcon, QPalette

#get qt version in list of ints
QT_VERSION = []
for strdigit in QT_VERSION_STR.split('.'):
    QT_VERSION.append(int(strdigit))

QT_VERSION = tuple(QT_VERSION)

if QT_VERSION < (5, 6):
    sys.stderr.write(
        "WARNING: You are using a version of QT older than 5.6.\n"
        + "You won't be able to know if a process can't be launch.\n")

#Ray Session version
VERSION = "0.6.1"

APP_TITLE = 'Ray Session'

class PrefixMode():
    UNDEF        = 0
    CLIENT_NAME  = 1
    SESSION_NAME = 2

class ClientStatus():
    STOPPED =  0
    LAUNCH  =  1
    OPEN    =  2
    READY   =  3
    PRECOPY =  4
    COPY    =  5
    SAVE    =  6
    SWITCH  =  7
    QUIT    =  8
    NOOP    =  9
    ERROR   = 10
    REMOVED = 11

class ServerStatus():
    OFF     =  0
    NEW     =  1
    OPEN    =  2
    CLEAR   =  3
    SWITCH  =  4
    LAUNCH  =  5
    PRECOPY =  6
    COPY    =  7
    READY   =  8
    SAVE    =  9
    CLOSE   = 10
    
class NSMMode():
    NO_NSM  = 0
    CHILD   = 1
    NETWORK = 2
    
class Option():
    NSM_LOCKED       = 0x001
    SAVE_FROM_CLIENT = 0x002
    BOOKMARK_SESSION = 0x004
    HAS_WMCTRL       = 0x008
    DESKTOPS_MEMORY  = 0x010

class Err():
    OK                =  0
    GENERAL_ERROR     = -1
    INCOMPATIBLE_API  = -2
    BLACKLISTED       = -3
    LAUNCH_FAILED     = -4
    NO_SUCH_FILE      = -5
    NO_SESSION_OPEN   = -6
    UNSAVED_CHANGES   = -7
    NOT_NOW           = -8
    BAD_PROJECT       = -9
    CREATE_FAILED     = -10
    SESSION_LOCKED    = -11
    OPERATION_PENDING = -12
    COPY_RUNNING      = -13
    NET_ROOT_RUNNING  = -14

class Command():
    NONE      = 0
    QUIT      = 1
    KILL      = 2
    SAVE      = 3
    OPEN      = 4
    START     = 5
    CLOSE     = 6
    DUPLICATE = 7
    NEW       = 8

class WaitFor():
    NONE     = 0
    STOP     = 1
    ANNOUNCE = 2
    REPLY    = 3
    DUPLICATE_START  = 4
    DUPLICATE_FINISH = 5

class Template():
    NONE             = 0
    RENAME           = 1
    SESSION_SAVE     = 2
    SESSION_SAVE_NET = 3
    SESSION_LOAD     = 4
    SESSION_LOAD_NET = 5
    CLIENT_SAVE      = 6
    CLIENT_LOAD      = 7

debug = False

def ifDebug(string):
    if debug:
        print(string, file=sys.stderr)

def setDebug(bool):
    global debug
    debug = bool

def getListInSettings(settings, path):
    #getting a QSettings value of list type seems to not works the same way on all machines
    try:
        settings_list = settings.value(path, [], type=list)
    except:
        try:
            settings_list = settings.value(path, [])
        except:
            settings_list = []
            
    return settings_list

def isPidChildOf(child_pid, parent_pid):
    if child_pid < parent_pid:
        return False
    
    ppid = child_pid
    this_pid = os.getpid()
    
    while ppid != parent_pid and ppid > 1 and ppid != this_pid:
        try:
            ppid = int(subprocess.check_output(['ps', '-o', 'ppid=', '-p', str(ppid)]))
        except:
            return False
        
    if ppid == parent_pid:
        return True
    
    return False

def isOscPortFree(port):
    try:
        testport = Server(port)
    except:
        return False
    
    del testport
    return True

def getFreeOscPort(default=16187):
    #get a free OSC port for daemon, start from default
    
    if default >= 65536:
        default=16187
    
    daemon_port = default
    UsedPort    = True
    testport    = None

    while UsedPort:
        try:
            testport = Server(daemon_port)
            UsedPort = False
        except:
            daemon_port += 1
            UsedPort = True

    del testport
    return daemon_port

def isValidOscUrl(url):
    try:
        address = liblo.Address(url)
        return True
    except:
        return False

def getLibloAddress(url):
    valid_url = False
    try:
        address = liblo.Address(url)
        valid_url = True
    except:
        valid_url = False
        msg = "%r is not a valid osc url" % url
        raise argparse.ArgumentTypeError(msg)
    
    if valid_url:
        try:
            liblo.send(address, '/ping')
            return address
        except:
            msg = "%r is an unknown osc url" % url
            raise argparse.ArgumentTypeError(msg)

def areSameOscPort(url1, url2):
    if url1 == url2:
        return True
    try:
        address1 = Address(url1)
        address2 = Address(url2)
    except:
        return False
    
    if address1.port != address2.port:
        return False
    
    if areOnSameMachine(url1, url2):
        return True
    
    return False
    
def areOnSameMachine(url1, url2):
    if url1 == url2:
        return True
    
    try:
        address1 = Address(url1)
        address2 = Address(url2)
    except:
        return False
    
    if address1.hostname == address2.hostname:
        return True
    
    try:
        if ((socket.gethostbyname(address1.hostname) in ('127.0.0.1', '127.0.1.1')) and
            (socket.gethostbyname(address2.hostname) in ('127.0.0.1', '127.0.1.1'))):
            return True
        
        if socket.gethostbyaddr(address1.hostname) == socket.gethostbyaddr(address2.hostname):
            return True
    except:
        try:
            ips = subprocess.check_output(['hostname', '-I']).decode()
            ip = ips.split(' ')[0]
            
            if ip.count('.') != 3:
                return False
        
            if not ip in (address1.hostname, address2.hostname):
                return False
            
            try:
                if socket.gethostbyname(address1.hostname) in ('127.0.0.1', '127.0.1.1'):
                    if address2.hostname == ip:
                        return True
            except:
                if socket.gethostbyname(address2.hostname) in ('127.0.0.1', '127.0.1.1'):
                    if address1.hostname == ip:
                        return True
        
        except:
            return False
        
        return False
    
    return False
    
def getUrl192(url):
    try:
        ips = subprocess.check_output(['hostname', '-I']).decode()
        ip = ips.split(' ')[0]
    except:
        return url
        
    if ip.count('.') != 3:
        return url
    
    suffix_port = url.rpartition(':')[2]
    return "osc.udp://%s:%s" % (ip, suffix_port)

def getThis192():
    global machine192
        
    if 'machine192' in globals():
        return machine192

    try:
        ips = subprocess.check_output(['hostname', '-I']).decode()
        ip = ips.split(' ')[0]
        machine192 = ip
        return ip
    except:
        return ''

def getMachine192(hostname=None):
    if hostname == None:
        return getThis192()
    else:
        if hostname in ('localhost', socket.gethostname()):
            return getThis192()
        
        return socket.gethostbyname(hostname)

def getMachine192ByUrl(url):
    try:
        addr = Address(url)
    except:
        return ''
    
    hostname = addr.hostname
    del addr
    
    return getMachine192(hostname)

def getNetUrl(port):
    try:
        ips = subprocess.check_output(['hostname', '-I']).decode()
        ip = ips.split(' ')[0]
    except:
        return ''
    
    if ip.count('.') != 3:
        return ''
    
    return "osc.udp://%s:%i/" % (ip, port)
    
def shellLineToArgs(string):
    try:
        args = shlex.split(string)
    except:
        return None
    
    return args

def areTheyAllString(args):
    for arg in args:
        if type(arg) != str:
            return False
    return True

def getAppIcon(icon_name, widget):
    dark = bool(widget.palette().brush(2, QPalette.WindowText).color().lightness() > 128)
    
    icon = QIcon.fromTheme(icon_name)
    
    if icon.isNull():
        for ext in ('svg', 'svgz', 'png'):
            filename = ":app_icons/%s.%s" % (icon_name, ext)
            darkname = ":app_icons/dark/%s.%s" % (icon_name, ext)
            
            if dark and QFile.exists(darkname):
                filename = darkname
            
            if QFile.exists(filename):
                del icon
                icon = QIcon()
                icon.addFile(filename)
                break
            
    return icon

class ClientData(object):
    client_id       = ''
    executable_path = ''
    arguments       = ''
    name            = ''
    prefix_mode     = 2
    project_path    = ''
    label           = ''
    icon            = ''
    capabilities    = ''
    check_last_save = True
    
    def __init__(self, client_id, 
                 executable,
                 arguments="",
                 name='', 
                 prefix_mode=PrefixMode.SESSION_NAME, 
                 project_path='', 
                 label='', 
                 icon='', 
                 capabilities='',
                 check_last_save=True):
        self.client_id       = str(client_id)
        self.executable_path = str(executable)
        self.arguments       = str(arguments)
        self.prefix_mode     = int(prefix_mode)
        self.label           = str(label)
        self.capabilities    = str(capabilities)
        self.check_last_save = bool(check_last_save)
        
        self.name  = str(name) if name else os.path.basename(self.executable_path)
        self.icon  = str(icon) if icon else self.name.lower().replace('_', '-')
        
        if self.prefix_mode == 0:
            if self.project_path:
                self.project_path = str(project_path)
            else:
                self.prefix_mode = 2

def clientStatusString(status):
    if not 0 <= status < len(client_status_strings):
        return _translate('client status', "invalid")
        
    return client_status_strings[status]

def serverStatusString(server_status):
    if not 0 <= server_status < len(server_status_strings):
        return _translate('server status', "invalid")
    
    return server_status_strings[server_status]

def init_translation(_translate):    
    global client_status_strings
    client_status_strings = {
        ClientStatus.STOPPED: _translate('client status', "stopped"),
        ClientStatus.LAUNCH : _translate('client status', "launch"),
        ClientStatus.OPEN   : _translate('client status', "open"),
        ClientStatus.READY  : _translate('client status', "ready"),
        ClientStatus.PRECOPY: _translate('client status', "copy"),
        ClientStatus.COPY   : _translate('client status', "copy"),
        ClientStatus.SAVE   : _translate('client status', "save"),
        ClientStatus.SWITCH : _translate('client status', "switch"),
        ClientStatus.QUIT   : _translate('client status', "quit"),
        ClientStatus.NOOP   : _translate('client status', "noop"),
        ClientStatus.ERROR  : _translate('client status', "error"),
        ClientStatus.REMOVED: _translate('client status', "removed") }
    
    global server_status_strings
    server_status_strings = {
        ServerStatus.OFF      : _translate('server status', "off"),
        ServerStatus.NEW      : _translate('server status', "new"),
        ServerStatus.OPEN     : _translate('server status', "open"),
        ServerStatus.CLEAR    : _translate('server status', "clear"),
        ServerStatus.SWITCH   : _translate('server status', "switch"),
        ServerStatus.LAUNCH   : _translate('server status', "launch"),
        ServerStatus.PRECOPY  : _translate('server status', "copy"),
        ServerStatus.COPY     : _translate('server status', "copy"),
        ServerStatus.READY    : _translate('server status', "ready"),
        ServerStatus.SAVE     : _translate('server status', "save"),
        ServerStatus.CLOSE    : _translate('server status', "close") }

        