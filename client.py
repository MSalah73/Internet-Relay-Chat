import socket
import sys
import select
import time
import signal

def timeout_handler(signum, frame):
    print "Logging off - Session Time Out"
    sys.exit()
def read(sock, data):
    try:
        file = open(data,"rb")
        sock.sendall("OK".encode("utf8"))
        fread = file.read(5120)
        while fread:
            sock.sendall(fread.encode("utf8"))
            fread = file.read(5120)
        sock.sendall("FILEDONE".encode("utf8"))
    except:
        sock.sendall("FILEFAILED".encode("utf8"))
        print "File does not exist"

def write(sock, data, file, write_mode):
    if data.find("FILEWRITE") != -1:
        write_mode = True
        _,data = data.split(" ", 1)
        print data
        try:
            file = open(data, "wb")
            sock.sendall("OK".encode("utf8"))
        except:
            print "File download failed"
            sock.sendall("NO".encode("utf8"))
            write_mode = False
    elif data.find("FILEDONE") != -1:
        data,_ = data.split("FILEDONE", 1)
        file.write(data)
        file.close()
        file = None
        print "file download is complate"
        write_mode = False   
    elif write_mode and data != "FILEWRITE":
        file.write(data)
    return write_mode, file

def main():
    if (len(sys.argv) < 5) | (len(sys.argv) > 5):
        print "Invalid uages of client program. Please run as client.py Username Hostname(or ip address) Port Realname."
        sys.exit()

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM) # create TCP socket


    realname = sys.argv[4]
    port = int(sys.argv[3])
    host = sys.argv[2]
    username = sys.argv[1]

    try:
        client_socket.connect((host, port))  # connect to remote
    except Exception as e:
        print(e)
        sys.exit()

    client_socket.sendall(username.encode("utf8"))
    time.sleep(.001)
    if client_socket.recv(5120).decode("utf8") == "noPass":
        print "Username is in use. Please try a different username."
        sys.exit()
    client_socket.sendall(realname.encode("utf8"))

    signal.signal(signal.SIGALRM, timeout_handler)
    signal.alarm(900)

    print "Welcome to IRC-Replica!\nPlease use the /help command for commands info and useage."
    message = ""
    temp_msg = []
    file = None
    write_mode = False
    sockets = [client_socket, sys.stdin] #sys.stdin get the user imput without waiting
    while ((message[0:5] != "/quit") & (message[0:2] != "/q")):
        try:
            read_sock, write_sock, exception = select.select(sockets,[],[])# this get the readable sockets 
        except:
            print "Client Interrupted\nShutting down..."
            sys.exit()

        for sock in read_sock:
            if sock == client_socket:
                data = client_socket.recv(5120).decode("utf8")

                if not data: # sever is down
                    print "Server is down"
                    sys.exit() 

                if data == "":
                    continue
                elif data.find("UPLOAD") != -1:
                    _,data = data.split(" ", 1)
                    read(sock, data)
                elif data.find("FILEWRITE") != -1 or write_mode:
                    write_mode, file = write(sock, data, file, write_mode)
                else:
                    print(data)
            else:
                signal.alarm(900)
                message = sys.stdin.readline(5120)

                if message == "\n":
                    continue
                else: 
                    client_socket.sendall(str(message).encode("utf8"))

if __name__ == "__main__":
    main()
