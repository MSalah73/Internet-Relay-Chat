import socket
import sys
import select
import time
from collections import OrderedDict
import re

"""     Server commands     """
def SQUIT(sock): 
    print "Quitting server..."
    sock.close()
    sys.exit()
"""     Client commands     """
def QUIT(sock, sockets, data): #/quit <message>
    print accounts[sock]["nickname"]+" disconected"

    for delete in accounts[sock]["channels"]:
        if len(users_inChannels[delete]["userlist"]) == 1:
            channel_names.remove(delete)
        else:
            users_inChannels[delete]["userlist"].remove(sock)

    if data:
        channel_broadcast(sock, accounts[sock]["channels"], ("\b\b has left the chat room\nMessage: "+data[0]))
    else:
        channel_broadcast(sock, accounts[sock]["channels"], "\b\b has left the chat room")
    sock.close()
    sockets.remove(sock)

def JOIN(sock, sockets, data):  #/join <channels> saparated by comma
    data = list(OrderedDict.fromkeys(data)) #remove dublicates
    for room in data:
        if not (room in channel_names):
            channel_names.append(room)
            users_inChannels[room] = {
                    "userlist": [sock]
                    }
        else:
            if sock in users_inChannels[room]["userlist"]:
                sock.sendall(("You already joined "+ room).encode("utf8"))
                continue
            else:
                users_inChannels[room]["userlist"].append(sock)
        
        accounts[sock]["channels"].append(room)
        if accounts[sock]["onDisplay"] == "":
            accounts[sock]["onDisplay"] = room
        channel_broadcast(sock, [room], "\b\b has joined the chat room")

def NICK(sock, sockets, data):
    if len(data) != 1:
        raise
    new = True
    if accounts[sock]["nickname"] == data[0]:
        sock.sendall(("Error: Nickname entered is the same as the current nickname").encode("utf8"))
        new = False
    elif re.match(r"(^Guest-\d+)\b", data[0]):
        sock.sendall(("Error: User can not change their nickname to Guest-#").encode("utf8"))
        new = False
    elif new:
        for soc in sockets:
            if soc == sockets[0] or soc == sockets[1]:
                continue
            elif accounts[soc]["nickname"] == data[0]:
                sock.sendall(("Error: Nickname is in use. Please try a different nickname").encode("utf8"))
                new = False
    if new:
        old_nick = accounts[sock]["nickname"] # name = names, guest-num, check list of names 
        new_nick = accounts[sock]["nickname"] = data[0]
        size = len(new_nick)+2 # 2 for the space and :
        sock.sendall(("You have changed your nickname to "+new_nick).encode("utf8"))
        print old_nick + " Change their name to "+ new_nick
        if accounts[sock]["channels"]:
            broadcast(sockets, sock,((size *"\b")+old_nick+" changed their nickname to "+new_nick))

def SWITCH(sock, sockets, data):
    if len(data) != 1 or '' == data[0]:
        raise
    if data[0] in accounts[sock]["channels"]:
        if data[0] == accounts[sock]["onDisplay"]:
            sock.sendall(("You are currently ondisplay on #"+data[0]))
        elif accounts[sock]["onDisplay"] == "":
            sock.sendall(("Setting your ondisplay on #"+data[0]))
        else:
            sock.sendall(("You have changed your current onDisplay from #"+accounts[sock]["onDisplay"]+" to #"+data[0]).encode("utf8"))
        accounts[sock]["onDisplay"] = data[0]
    else:
        sock.sendall(("You are not connected to "+data[0]).encode("utf8"))
   
def LIST(sock, sockets, data):
    data = list(OrderedDict.fromkeys(data)) #remove dublicates
    if '' in data:
        raise 
    elif not channel_names:
        sock.sendall("Server does not have any channels".encode("utf8"))
        pass
    elif not data:
        sock.sendall("All Channels:".encode("utf8"))
        time.sleep(0.0001)
        for room in channel_names:
            sock.sendall(room.encode("utf8"))
            time.sleep(0.00001)
    else:
        if not set(data).isdisjoint(set(channel_names)): 
            sock.sendall("Requested Channels:".encode("utf8"))
            time.sleep(0.00001)
            for room in channel_names:
                if room in data:
                    sock.sendall(("#"+room).encode("utf8"))
                    time.sleep(0.00001)

        for request in data:
            if request not in channel_names:
                sock.sendall("Requested channel #"+request+" does not exit".encode("utf8"))
                time.sleep(0.00001)

def PART(sock, sockets, data):
    message = ''
    last_item = len(data)-1 
    if data[last_item][0:2] == "XX":
        message = data[last_item][2:]
        data.pop(last_item)

    data = list(OrderedDict.fromkeys(data)) #remove dublicates
    parted = []

    if not set(data).isdisjoint(set(channel_names)) and not set(data).isdisjoint(set(accounts[sock]["channels"])): 
        sock.sendall("channels parted:".encode("utf8"))
        for channel in data:
            if channel in accounts[sock]["channels"]:
                sock.sendall(("#"+channel).encode("utf8"))
                accounts[sock]["channels"].remove(channel)
                users_inChannels[channel]["userlist"].remove(sock)
                parted.append(channel)
                if accounts[sock]["onDisplay"] == channel:
                    accounts[sock]["onDisplay"] = ""
    if parted:
        if message != '':
            channel_broadcast(sock, parted, ("\b\b has left the chat room\nMessage: "+message))
        else:
            channel_broadcast(sock, parted, "\b\b has left the chat room")

    for request in data:
        if request not in accounts[sock]["channels"] and request in channel_names and request not in parted:
            sock.sendall(("You can not leave #"+request+" becouse you are not part of it").encode("utf8"))
            time.sleep(0.00001)
        elif request not in channel_names:
            sock.sendall("Requested channel #"+request+" does exit".encode("utf8"))
            time.sleep(0.00001)

    for delete in parted:
        if not users_inChannels[delete]["userlist"]:
            channel_names.remove(delete)

def NAMES(sock, sockets, data):
    data = list(OrderedDict.fromkeys(data)) #remove dublicates
    for channel in data:
        if channel not in channel_names:
            sock.sendall("Requested channel #"+channel+" does exit".encode("utf8"))
            continue
        sock.sendall(("Users in channel #"+channel+":").encode("utf8"))
        time.sleep(0.00001)
        for user in users_inChannels[channel]["userlist"]:
            WHOIS(sock, sockets, [accounts[user]["nickname"]])
            time.sleep(0.00001)

def WHOIS(sock, sockets, data):  #whois need aligemnets every run is diff
    data = list(OrderedDict.fromkeys(data)) #remove dublicates
    for nick in data: #we can also make the client handles the all the chain of sends
        found = False
        for soc in sockets:
            if soc == sockets[0] or soc == sockets[1]:
                continue
            if nick == accounts[soc]["nickname"]:
                sock.sendall((nick+"'s Info:").encode("utf8"))
                time.sleep(0.00001) #we can saparate lines so recv would not get two of the sends
                sock.sendall(("Username: "+accounts[soc]["username"]).encode("utf8"))
                time.sleep(0.00001)
                sock.sendall(("Current Channel: "+accounts[soc]["onDisplay"]).encode("utf8"))
                time.sleep(0.00001)
                sock.sendall(("Channels connected:").encode("utf8"))
                time.sleep(0.00001)
                for room in accounts[soc]["channels"]:
                    sock.sendall(("#"+room).encode("utf8"))
                    time.sleep(0.00001)
                found = True
        if not found:
            sock.sendall(("Requested user's nickname: "+nick+" does not exist.").encode("utf8"))
            time.sleep(0.00001)
                    


def BCAST(sock, sockets, data):    #boardcast a message to spacifed channels
    message = ''
    last_item = len(data)-1 
    if data[last_item][0:2] == "XX":
        message = data[last_item][2:]
        data.pop(last_item)
    else:
        raise
    data = list(OrderedDict.fromkeys(data)) #remove dublicates

    if not set(data).isdisjoint(set(channel_names)) and not set(data).isdisjoint(set(accounts[sock]["channels"])): 
        sock.sendall("Message sent to channels: ".encode("utf8"))
        for channel in data:
            if channel in accounts[sock]["channels"]:
                time.sleep(0.00001)
                sock.sendall(("#"+channel+" ").encode("utf8"))
                channel_broadcast(sock, channel,("\b\b is broadcasting #"+channel+" a message\nmessage: "+message))


    for request in data:
        if request not in accounts[sock]["channels"] and request in channel_names:
            sock.sendall(("You can not broadcast a message to #"+request+" becouse you are not part of it").encode("utf8"))
            time.sleep(0.00001)
        elif request not in channel_names:
            sock.sendall("Requested channel #"+request+" does exit".encode("utf8"))
            time.sleep(0.00001)


def PRIVMSG(sock, sockets, data): #nick or channel 
    if len(data) != 2:
        raise
    if data[0] in channel_names:
        channel_broadcast(sock, data[0],("\b\b has sent broadcasted a private message\nmessage:"+data[1]))
    else:
        for soc in sockets:
            if soc == sock or soc == sockets[0] or soc == sockets[1]:
                continue
            if accounts[soc]["nickname"] == data[0]:
                soc.sendall((accounts[sock]["nickname"]+" sent a private message to you\nMessage: "+data[1]).encode("utf8"))

def HELP(sock, sockets, data):
    sock.sendall("Note: channel names and nicknames are restricted to [A-Za-z9-0_-.?] and no spaces".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("Joining a channel -->  Note: You may use /j as a short cut.".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("Quiting --> /quit or /quit message. Note: You may use /q as a short cut.".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("List channels --> /list #channel_name, #channel_name2-> to list specified channels or /list ->list all channels".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("Switch channels --> /switch #channel_name".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("Leave a channel/s --> /part #channel_name, #channel_name2 or /part #channel_name, #channel_name2 message".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("List users info in channel/s --> /names #channel_name, #channel_name2".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("Broadcast a message to channel/s --> /bcast #channel_name, #channel_name2 message".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("List user/s info --> /whois nickname, nickname2".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("Sending a private message to a user or a channel --> /privmsg #channel_name message or /privmsg nickname message".encode("utf8"))
    time.sleep(0.00001)
    sock.sendall("Changing your nickname --> /nick new_nickname".encode("utf8"))
    time.sleep(0.00001)

def FSEND(sock, sockets, data):
    sock.sendall(("UPLOAD "+data[0]).encode("utf8"))
    if sock.recv(5120) == "OK":
        try:
            file = open(data[1], "wb")
            to_write = sock.recv(5120)
            while to_write:
                if to_write.find("FILEDONE") != -1:
                    to_write,_ = to_write.split("FILEDONE",1)
                    file.write(to_write)
                    to_write = None
                else:
                    file.write(to_write)
            file.close()
            sock.sendall("Upload successful".encode("utf8"))
        except:
            print "Uplaod failed"

def FRECV(sock, sockets, data):
    try:
        file = open(data[0], "rb")
        read = file.read(5120)
        sock.sendall(("FILEWRITE "+data[1]).encode("utf8"))
        time.sleep(0.00001)
        if sock.recv(5120) == "OK":
            while read:
                sock.sendall(read.encode("utf8"))
                read = file.read(5120)
            sock.sendall("FILEDONE".encode("utf8"))
            file.close()
        else:
            print "Sending file failed"
            file.close()
    except:
        sock.sendall((data[0]+ " does not exist").encode("utf8"))
        

command_list = {
        "/quit":    QUIT,      "/q":       QUIT,
        "/join":    JOIN,      "/j":       JOIN,
        "/switch":  SWITCH,    "/list":    LIST,
        "/part":    PART,      "/names":   NAMES,
        "/whois":   WHOIS,     "/bcast":   BCAST,
        "/privmsg": PRIVMSG,   "/help":    HELP,
        "/nick":    NICK,      "/fsend":   FSEND,
        "/frecv":   FRECV,    
        }
server_command_list = {
        "/squit":   SQUIT,     "/sq":      SQUIT,
        }
accounts = {}
channel_names = []
users_inChannels = {}

def main():
    start_server()


def start_server():
    host = socket.gethostname()
    port = 5000  # arbitrary non-privileged port

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR,1)  # SO_REUSEADDR flag tells the kernel to reuse a local socket in TIME_WAIT state, without waiting for its natural timeout to expire
    print("Socket created")

    try:
        server.bind((host, port))
    except:
        print("Bind failed. Error : " + str(sys.exc_info()))
        sys.exit()

    print("Server info:\nHost: " + socket.gethostbyname(host) + "\nPort: " + str(port))

    server.listen(5)  # queue up to 5 requests
    print("Socket now listening")

    _input = [server, sys.stdin]
    running = 1
    guest_name_counter = 1
    while running:
        try:
            input_ready, output_ready, except_ready = select.select(_input, [], [])
        except:
            print "Error: Server interrupted\nShutting down..."
            server.close()
            sys.exit()

        for sock in input_ready:

            if sock == server:
                # handle the server socket
                client, address = server.accept()
                ip, port = str(address[0]), str(address[1])
                username = client.recv(5120).decode("utf8")
                new = True
                for soc in _input:
                    if soc != server and soc != sys.stdin and accounts[soc]["username"] == username:
                        new = False
                if new:
                    print("Connected with " + ip + ":" + port)
                    client.sendall("Pass".encode("utf8"))
                    _input.append(client)
                    accounts[client] = {
                        "username"  :   username,
                        "realname"  :   client.recv(5120).decode("utf8"),
                        "nickname"  :   ("Guest-" + str(guest_name_counter)),
                        "channels"  :   [],
                        "onDisplay" :   "",
                        }
                    guest_name_counter += 1
                else:
                    client.sendall("noPass".encode("utf8"))
            elif sock == sys.stdin:
                command = process_input("Server", sys.stdin.readline(5120), max_buffer_size=5120)
                if re.match(r"^(/sq|/squit)\s*?$",command):
                    server_command_list[command](server)
                else:
                    print "Invalid command"
            else:
                # handle all other sockets
                try:
                    data = sock.recv(5120)
                except Exception as e:
                    print e
                    sys.exit()
                if not data:
                    QUIT(sock, _input, "")
                    continue

                else:
                    data = process_input(accounts[sock]["nickname"], data,max_buffer_size=5120)
                    if not data:
                        continue
                    elif data[0] == "/":# parse the input
                        data, to_send = command_parser(data)
                        try:
                            command_list[data](sock, _input, to_send)
                        except:
                            sock.sendall("Invalid command".encode("utf8"))
                    else:
                        broadcast(_input, sock, data)


    server.close()
def command_parser(data):
    if re.match(r"^((/j|/join|/list|/switch|/names|/part)\s+?#(([?.\w-]+?),\s*?#)*?)([?.\w-]+?)\s*?$",data):
        data, args = parse_data(data, [], "#", False)
    elif re.match(r"^((/part|/bcast|/privmsg)\s+?#(([?.\w-]+?),\s*?#)*?)([?.\w-]+?)\s+?.+?$",data):
        data, args = parse_data(data, [], "#", True)
    elif re.match(r"^(((/whois|/nick)\s+?(([?.\w-]+?),\s*?)*?)([?.\w-]+?)\s*?)|((/help|/list)\s*?)|((/fsend|/frecv)(\s+?([?.\w-]+?).txt){2})$", data):
        data, args = parse_data(data, [], " ", False)
    elif re.match(r"^((/q|/quit)((\s+?.+?)|(\s*?)))|(/privmsg\s+?[?.\w-]+?\s+?.+?)$", data):
        string = data.split(" ", 1)
        data = string[0].rstrip()
        if data == "/privmsg":
            string = string[1].split(" ", 1)
            args = [string[0],string[1]]
        elif len(string) == 2:
            args = [string[1]]
        else:
            args = None
    else:
        data, args = None, None

    return data, args

def parse_data(data, args, split_char , msg_flag):
    try:
        split_str = data.split(split_char)
        split_len = len(split_str)
        for string in split_str:
            if string == split_str[0]:
                data = string
                continue
            try:
                if msg_flag and string == split_str[split_len-1]:
                    arg, message = string.split(" ", 1)
                    args.append(arg)
                    args.append(("XX"+message))
                else:
                    arg, _ = string.split(",")
                    args.append(arg)
            except:
                args.append(string)

        data = data.rstrip()
    except:
        args = []
    return data, args

def broadcast(sockets, sock, data):
    if not accounts[sock]["channels"]:
        sock.sendall("You are not connected to any channel. Please use the join command".encode("utf8"))
    elif accounts[sock]["onDisplay"] == '': 
        sock.sendall("You are not onDisplay on any channel. Please use the switch command to be onDiplay on connected channels".encode("utf8"))
    else:
        for to_send in sockets:
            if sock != to_send and (sockets[0] != to_send and sockets[1] != to_send) and (accounts[sock]["onDisplay"] == accounts[to_send]["onDisplay"]):
                try:
                    to_send.sendall((accounts[sock]["nickname"]+": "+data).encode("utf8"))
                except:
                    continue
def channel_broadcast(sock, channels, data):
    user_list = []
    for channel in channels: 
        user_list.extend(users_inChannels[channel]["userlist"])

    user_list = OrderedDict.fromkeys(user_list) #remove dublicates
    for user in user_list:
        if sock != user:
            try:
                user.sendall((accounts[sock]["nickname"]+": "+data).encode("utf8"))
            except:
                continue

def process_input(username, client_input, max_buffer_size):
    client_input_size = sys.getsizeof(client_input)

    if client_input_size > max_buffer_size:
        print("The input size is greater than expected {}".format(client_input_size))

    decoded_input = client_input.decode("utf8").rstrip()  # decode and strip end of line
    if username != "Server":
        print("Processing the input received from "+username)

    return str(decoded_input)


if __name__ == "__main__":
    main()
