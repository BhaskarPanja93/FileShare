from os import walk, getcwd, path, remove
from subprocess import call
from platform import system
from random import randrange
from threading import Thread
import socket
from time import sleep, time


secret_key = b''
FILES_CURRENTLY_SENDING = FILES_SENT = SIZE_SENT = SIZE_RECEIVED = FILES_QUEUED_UP = 0
receiver_ip = ''
reachable_port = None
BUFFER_SIZE = 1024*10
FINISHED = False
USER_DEFINED_LIMIT = 50



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


def find_reachable_port(ip: str, port: int, connection_type: str):
    global reachable_port
    if connection_type == 'tcp':
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    connection.settimeout(5)
    try:
        connection.connect((ip, port))
        __send_to_connection(connection, b'reach')
        if __receive_from_connection(connection) == b'pass':
            if not reachable_port:
                reachable_port = port
    except:
        pass


def __force_connect_to_receiver(ip, port, connection_type):
    if connection_type == 'tcp':
        connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    else:
        connection = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    while True:
        try:
            connection.connect((ip, port))
            break
        except:
            pass
    return connection


def address_translator(receiver_address: str):
    global receiver_ip, reachable_port, secret_key
    if ':' in receiver_address: #global address not implemented
        receiver_ip, reachable_port = receiver_address.split(':')
    else:
        receiver_ip = receiver_address
        for port in range(65534,1,-500):
            if reachable_port:
                break
            else:
                Thread(target=find_reachable_port, args=(receiver_ip, port, 'tcp',)).start()
        else:
            sleep(2)
            if not reachable_port:
                print('[No Open Ports] Unable to connect to destination address...')
                while not reachable_port:
                    sleep(1)
    if not secret_key:
        for _ in range(4):
            secret_key += chr(randrange(97, 123)).encode()
    print(f"Connected")
    print(f"Enter this Secret Key on Receiving Side: {secret_key.decode()}")
    filename_iterator()



def filename_iterator():
    global FILES_CURRENTLY_SENDING, FILES_QUEUED_UP
    for full_path, folders, files in walk(getcwd()):
        for filename in files:
            while FILES_CURRENTLY_SENDING + FILES_QUEUED_UP >= MAX_SIMULTANEOUS_FILES:
                sleep(0.5)
            FILES_QUEUED_UP += 1
            Thread(target=authenticate_with_receiver, args=(full_path, filename)).start()



def authenticate_with_receiver(full_path, filename):
    global secret_key, receiver_ip, reachable_port, FILES_CURRENTLY_SENDING, FILES_QUEUED_UP
    connection = __force_connect_to_receiver(receiver_ip, reachable_port, 'tcp')
    try:
        if __receive_from_connection(connection) == secret_key:
            __send_to_connection(connection, b'0')

            Thread(target=__send_individual_file, args=(connection, full_path, filename,)).start()
        else:
            authenticate_with_receiver(full_path, filename)
    except:
        FILES_QUEUED_UP -= 1
        authenticate_with_receiver(full_path, filename)


def __send_individual_file(connection, full_path, filename):
    global FILES_CURRENTLY_SENDING, FILES_SENT, SIZE_SENT, FILES_QUEUED_UP
    try:
        FILES_QUEUED_UP -= 1
        FILES_CURRENTLY_SENDING += 1
        relative_path = full_path.replace(getcwd() + '/', '').replace(getcwd() + '\\', '').replace(getcwd(), '')
        __send_to_connection(connection, path.join(relative_path, filename).replace('\\', '/').encode())
        with open(path.join(relative_path, filename), 'rb') as file:
            while True:
                partial_file_data = file.read(BUFFER_SIZE)
                if partial_file_data:
                    __send_file_data(connection, partial_file_data)
                else:
                    __send_file_data(connection, False)
                    break
        if __receive_from_connection(connection) == b'{-0}':
            FILES_SENT += 1
            FILES_CURRENTLY_SENDING -= 1
            connection.close()
    except:
        authenticate_with_receiver(full_path, filename)



def __send_file_data(connection, partial_file_data):
    global SIZE_SENT
    if partial_file_data:
        data_length = len(partial_file_data)
        SIZE_SENT += data_length
        connection.send(f"{'0'*(15-len(str(data_length)))}{data_length}".encode())
        connection.send(partial_file_data)
        if connection.recv(1) == b'-':
            return
    else:
        connection.send(f"{'0' * 15}".encode())
        if connection.recv(1) == b'-':
            return



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
    global FILES_CURRENTLY_SENDING, FINISHED
    while FILES_CURRENTLY_SENDING == 0:
        sleep(0.1)
    s_time = time()
    while not FINISHED:
        if FILES_CURRENTLY_SENDING != 0:
            sleep(0.5)
        else:
            FINISHED = True
        if not FINISHED:
            if system() == 'Windows':
                call('cls', shell=True)
            else:
                call('clear', shell=True)
            print('-' * 15, flush=True)
            print('SENDING REPORT', flush=True)
            print('-' * 15, flush=True)
            print(f"Currently: {FILES_CURRENTLY_SENDING} Files", flush=True)
            print(f"Completed: {FILES_SENT} Files", flush=True)
            print(f"Sent Data: {size_calculator(SIZE_SENT)}", flush=True)
            print(f"Received Data: {size_calculator(SIZE_RECEIVED)}", flush=True)
            print(f"Time Elapsed: {int(time()-s_time)} seconds", flush=True)
    print('-' * 9, flush=True)
    print('FINISHED')
    print('-' * 9, flush=True)
    input()



Thread(target=address_translator, args=(input("Enter Address of Receiver> "),)).start()
Thread(target=update_screen).start()

