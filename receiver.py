from os import makedirs, remove
from subprocess import call
from platform import system
import socket
from threading import Thread
from time import sleep, time

secret_key = b''
FILES_CURRENTLY_RECEIVING = FILES_RECEIVED = SIZE_RECEIVED = SIZE_SENT = 0
secret_key_accepted = False
reachable_port = None
BUFFER_SIZE = 1024*1024
FINISHED = False
USER_DEFINED_LIMIT = 500


MAX_SIMULTANEOUS_FILES = 0
i = 0
while True:
    i+=1
    try:
        globals()[f"_{i}"] = open('x','ab')
    except:
        MAX_SIMULTANEOUS_FILES = True
    finally:
        if MAX_SIMULTANEOUS_FILES or i == USER_DEFINED_LIMIT * 2:
            MAX_SIMULTANEOUS_FILES = int(i // 2)
            for _ in range(i+1):
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


def duration_calculator(start: float, end: float):
    final_duration = ''
    duration_tree = []
    units = ['sec', 'minute', 'hour', 'day']



def host_ports_for_reachability(port):
    global reachable_port
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('0.0.0.0', port))
        sock.listen()
        while True:
            while reachable_port:
                sleep(1)
            connection, address = sock.accept()
            while reachable_port:
                sleep(1)
            reachable_port = True
            current_port = True
            if __receive_from_connection(connection) == b'reach':
                while reachable_port and not current_port:
                    sleep(1)
                __send_to_connection(connection, b'pass')
                reachable_port = port
                sock.close()
            else:
                reachable_port = None
    except:
        pass


def __initial_authenticator():
    global secret_key, secret_key_accepted
    local_ip = socket.gethostbyname_ex(socket.gethostname())[-1]
    if local_ip[0:3] == '127':
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(('10.255.255.255', 1))
        local_ip = s.getsockname()[0]
    print(f'waiting at...  {local_ip}')
    for port in range(65534, 1, -500):
        Thread(target=host_ports_for_reachability, args=(port,)).start()
    while type(reachable_port) != int:
        sleep(1)
    print(f"Connected")
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(('0.0.0.0', reachable_port))
    sock.listen()
    while True:
        if secret_key:
            if FILES_CURRENTLY_RECEIVING < MAX_SIMULTANEOUS_FILES:
                connection, address = sock.accept()
                if not secret_key_accepted:
                    authenticate_with_sender(connection)
                else:
                    Thread(target=authenticate_with_sender, args=(connection,)).start()
        else:
            secret_key = input("Enter Secret Key as shown in sender: ").encode()


def authenticate_with_sender(connection):
    global secret_key, secret_key_accepted
    try:
        __send_to_connection(connection, secret_key)
        if __receive_from_connection(connection) == b'0':
            secret_key_accepted = True
            Thread(target=__file_receive, args=(connection,)).start()
        else:
            __send_to_connection(connection, b'-1')
            connection.close()
            secret_key = b''
            secret_key = input("Wrong Secret Key entered try again: ").encode()
    except:
        try:
            connection.close()
        except:
            pass


def __file_receive(connection):
    global FILES_CURRENTLY_RECEIVING, FILES_RECEIVED
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
                data = __receive_file_data(connection)
                if data:
                    file.write(data)
                else:
                    file.close()
                    break
        sleep(1)
        FILES_CURRENTLY_RECEIVING -= 1
        __send_to_connection(connection, b'{-0}')
        FILES_RECEIVED += 1
        connection.close()
    except:
        try:
            connection.close()
        except:
            pass



def __receive_file_data(connection):
    global SIZE_RECEIVED
    length = b''
    while len(length) != 15:
        length += connection.recv(15- len(length))
    length = int(length)
    SIZE_RECEIVED += length
    if length:
        data = b''
        while len(data) != length:
            data += connection.recv(length - len(data))
        connection.send(b'-')
        return data
    else:
        connection.send(b'-')
        return False


def __send_to_connection(connection, data_bytes: bytes):
    global SIZE_SENT
    data_byte_length = len(data_bytes)
    connection.send(str(data_byte_length).encode())
    if connection.recv(1) == b'-':
        connection.send(data_bytes)
    if connection.recv(1) == b'-':
        SIZE_SENT += data_byte_length


def __receive_from_connection(connection):
    global SIZE_RECEIVED
    length = int(connection.recv(BUFFER_SIZE))
    connection.send(b'-')
    data_bytes = b''
    while len(data_bytes) != length:
        data_bytes += connection.recv(BUFFER_SIZE)
    connection.send(b'-')
    SIZE_RECEIVED += length
    return data_bytes




def update_screen():
    global FILES_CURRENTLY_RECEIVING, FINISHED
    while FILES_CURRENTLY_RECEIVING == 0:
        sleep(0.1)
    s_time = time()
    while not FINISHED:
        if FILES_CURRENTLY_RECEIVING != 0:
            sleep(0.5)
        else:
            FINISHED = True
        if not FINISHED:
            if system() == 'Windows':
                call('cls', shell=True)
            else:
                call('clear', shell=True)
            print('-' * 17, flush=True)
            print('RECEIVING REPORT', flush=True)
            print('-' * 17, flush=True)
            print(f"Currently: {FILES_CURRENTLY_RECEIVING} Files", flush=True)
            print(f"Completed: {FILES_RECEIVED} Files", flush=True)
            print(f"Sent Data: {size_calculator(SIZE_SENT)}", flush=True)
            print(f"Received Data: {size_calculator(SIZE_RECEIVED)}", flush=True)
            print(f"Time Elapsed: {int(time()-s_time)} seconds", flush=True)
    print('-' * 9, flush=True)
    print('FINISHED')
    print('-' * 9, flush=True)
    input()

Thread(target=__initial_authenticator).start()
Thread(target=update_screen).start()

