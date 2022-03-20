from os import makedirs, remove
from subprocess import call
from platform import system
import socket
from threading import Thread
from time import sleep, time
secret_key = b''
FILES_CURRENTLY_RECEIVING=0
FILES_RECEIVED = 0
SIZE_RECEIVED = 0
SERVER_MIGRATION_PORT = 60000
BUFFER_SIZE = 1024*5
FINISHED = False



"""if system() == 'Windows':
    system_caller(f'netsh advfirewall firewall add rule name= "_BhaskarFileTransfer" dir=in action=allow protocol=TCP localport={SERVER_MIGRATION_PORT}')"""

for _ in range(10000):
    try:
        globals()[f"_{_}"] = open('x','ab')
    except:
        MAX_SIMULTANEOUS_FILES=int(_*0.5)
        for _ in range(_):
            try:
                globals()[f"_{_}"].close()
                del globals()[f"_{_}"]
            except:
                pass
        break
remove('x')

def size_calculator(file_size_raw: int):
    file_size=''
    file_size_tree=[]
    size_units=['B','KB','MB','GB','TB','PB', 'EB', 'ZB', 'YB']
    while file_size_raw > 1024:
        file_size_tree.append(file_size_raw%1024)
        file_size_raw=file_size_raw//1024
    else:
        file_size_tree.append(file_size_raw)

    for i in range(len(file_size_tree)):
        file_size_tree[i]=str(file_size_tree[i])+size_units[i]
    file_size_tree.reverse()
    for size_value in file_size_tree:
        if size_value[0]!='0':
            file_size+=str(size_value)+' '
    return file_size



def __initial_authenticator():
    global secret_key
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('0.0.0.0', SERVER_MIGRATION_PORT))
    sock.listen()
    local_ip = socket.gethostbyname_ex(socket.gethostname())[-1]
    if local_ip[0:3] == '127':
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    print(f'waiting at...  {local_ip}')
    while True:
        if secret_key:
            if FILES_CURRENTLY_RECEIVING < MAX_SIMULTANEOUS_FILES:
                connection, address = sock.accept()
                if __receive_from_connection(connection) == secret_key:
                    __send_to_connection(connection, b'0')
                    Thread(target=__file_receive, args=(connection,)).start()
                else:
                    __send_to_connection(connection, b'-1')
                    connection.close()
                    secret_key = input("Wrong Secret Key entered try again: ").encode()
        else:
            secret_key = input("Enter Secret Key as shown in sender: ").encode()



def __file_receive(connection):
    global FILES_CURRENTLY_RECEIVING, FILES_RECEIVED, SIZE_RECEIVED
    try:
        FILES_CURRENTLY_RECEIVING += 1
        path = __receive_from_connection(connection).decode()
        try:
            open(path, 'wb').close()
        except FileNotFoundError:
            temp = path.split('/')
            del temp[-1]
            folder_name = ''
            for _ in temp:
                folder_name += _ + '/'
            makedirs(folder_name, exist_ok=True)
            open(path, 'wb').close()
        with open(path, 'ab') as file:
            while True:
                partial_file_data = __receive_from_connection(connection)
                if partial_file_data != b'{-0}':
                    SIZE_RECEIVED += len(partial_file_data)
                    file.write(partial_file_data)
                else:
                    file.close()
                    break
        sleep(1)
        FILES_CURRENTLY_RECEIVING -= 1
        __send_to_connection(connection, b'{-0}')
        FILES_RECEIVED += 1
        connection.close()
    except:
        FILES_CURRENTLY_RECEIVING -= 1


def __send_to_connection(connection, data_bytes: bytes):
    connection.send(str(len(data_bytes)).encode())
    if connection.recv(1) == b'-':
        connection.send(data_bytes)
    if connection.recv(1) == b'-':
        return


def __receive_from_connection(connection):
    length = int(connection.recv(BUFFER_SIZE))
    connection.send(b'-')
    data_bytes = b''
    while len(data_bytes) != length:
        data_bytes += connection.recv(BUFFER_SIZE)
    connection.send(b'-')
    return data_bytes


def receiving_complete():
    global FINISHED
    while FILES_CURRENTLY_RECEIVING == 0:
        sleep(1)
    s_time = time()
    Thread(target=update_screen).start()
    while FILES_CURRENTLY_RECEIVING != 0:
        sleep(1)
    f_time = time()
    FINISHED = True
    """if system() == 'Windows':
        system_caller(f'netsh advfirewall firewall delete rule name="_BhaskarFileTransfer"')"""
    print('Receiving Complete', flush=True)
    print(f"Total Received: {FILES_RECEIVED} Files ({size_calculator(SIZE_RECEIVED)})", flush=True)
    print(f"Time Taken: {int(f_time-s_time)}seconds with Buffer_size: {BUFFER_SIZE}", flush=True)
    input()

def update_screen():
    global FILES_CURRENTLY_RECEIVING, FINISHED
    while not FINISHED:
        if system() == 'Windows':
            call('cls', shell=True)
        else:
            call('clear', shell=True)
        print(f"Currently receiving: {FILES_CURRENTLY_RECEIVING} Files", flush=True)
        print(f"Total Received: {FILES_RECEIVED} Files ({size_calculator(SIZE_RECEIVED)})", flush=True)
        sleep(1/2)

Thread(target=__initial_authenticator).start()
Thread(target=receiving_complete).start()

