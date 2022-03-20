from os import walk, getcwd, path, remove, stat
from subprocess import call
from platform import system
from random import randrange
from threading import Thread
import socket
from time import sleep, time



FILES_CURRENTLY_SENDING = 0
FILES_SENT = 0
SIZE_SENT = 0
SERVER_MIGRATION_PORT = 60000
BUFFER_SIZE = 1024*5
FINISHED = False

secret_key = b''
for _ in range(5):
    secret_key += chr(randrange(97,123)).encode()
print(f"Enter this Secret Key on Receiving Side: {secret_key.decode()}")


for _ in range(10000):
    try:
        globals()[f"_{_}"] = open('x','ab')
    except:
        MAX_SIMULTANEOUS_FILES=int(_*0.4)
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



def __initial_authenticate(new_server_ip):
    global FILES_CURRENTLY_SENDING
    for full_path, folders, files in walk(getcwd()):
        for filename in files:
            while True:
                while FILES_CURRENTLY_SENDING >= MAX_SIMULTANEOUS_FILES:
                    sleep(1)
                connection = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                while True:
                    try:
                        connection.connect((new_server_ip, SERVER_MIGRATION_PORT))
                        break
                    except:
                        pass
                __send_to_connection(connection, secret_key)
                if b'0' == __receive_from_connection(connection):
                    FILES_CURRENTLY_SENDING += 1
                    Thread(target=__send_individual_file, args=(connection, full_path, filename,)).start()
                    break


def __send_individual_file(connection, full_path, filename):
    global FILES_CURRENTLY_SENDING, FILES_SENT, SIZE_SENT
    try:
            relative_path = full_path.replace(getcwd() + '/', '').replace(getcwd() + '\\', '').replace(getcwd(), '')
            __send_to_connection(connection, path.join(relative_path, filename).replace('\\', '/').encode())
            __send_to_connection(connection, str(stat(path.join(relative_path, filename).replace('\\', '/').encode()).st_size).encode())
            with open(path.join(relative_path, filename), 'rb') as file:
                while True:
                    partial_file_data = file.read(BUFFER_SIZE)
                    if partial_file_data:
                        SIZE_SENT += len(partial_file_data)
                        __send_to_connection(connection, partial_file_data)
                    else:
                        __send_to_connection(connection, b'{-0}')
                        break
            if __receive_from_connection(connection) == b'{-0}':
                FILES_SENT += 1
                FILES_CURRENTLY_SENDING -= 1
                connection.close()
    except:
        __send_individual_file(connection, full_path, filename)


def __send_to_connection(connection, data_bytes: bytes):
    data_byte_length = len(data_bytes)
    connection.send(str(data_byte_length).encode())
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


def sending_complete():
    global FINISHED
    while FILES_CURRENTLY_SENDING == 0:
        sleep(1)
    s_time = time()
    Thread(target=update_screen).start()
    while FILES_CURRENTLY_SENDING != 0:
        sleep(1)
    f_time = time()
    FINISHED = True
    print('Sending Complete', flush=True)
    print(f"Time Taken: {int(f_time-s_time)}seconds with Buffer_size: {BUFFER_SIZE}", flush=True)
    print(f"Total Sent: {FILES_SENT} Files ({size_calculator(SIZE_SENT)})", flush=True)
    input()

def update_screen():
    global FILES_CURRENTLY_SENDING, FINISHED
    while not FINISHED:
        if system() == 'Windows':
            call('cls', shell=True)
        else:
            call('clear', shell=True)
        print(f"Currently Sending: {FILES_CURRENTLY_SENDING} Files", flush=True)
        print(f"Total Sent: {FILES_SENT} Files ({size_calculator(SIZE_SENT)})", flush=True)
        sleep(1/2)

Thread(target=__initial_authenticate, args=(input("Enter IP Address of Receiver> "),)).start()
Thread(target=sending_complete).start()

