import socket
import threading
import json
import time
import uuid
import base64

CHAT_SERVER_NAME = 'server'

HOST = '127.0.0.1'  # 主机地址
PORT = 8888  # 端口号
BUFFSIZE = 2048  # 缓存区大小，单位是字节，这里设定了2K的缓冲区
ADDR = (HOST, PORT)  # 链接地址

grouplist = {}  # 群聊列表

image_fold_path = '/Users/rodrick/Documents/python/Chatroom/server_temp/img/'
file_fold_path = '/Users/rodrick/Documents/python/Chatroom/server_temp/file/'


# 公用函数
def get_keys(list, value_list):
    return [k for k, v in list.items() if v in value_list]


class User:
    def __init__(self, address, tcpCliSock):
        self.address = address
        self.tcpCliSock = tcpCliSock


class Handle:
    userlist = {}  # 用户列表,User对象
    usernames = []  # 用户名列表

    def __init__(self, user):
        self.user = user

    def login(self, data):
        """处理登录信息包"""
        if data["username"] in Handle.userlist.values() or self.user in Handle.userlist.keys():
            data['status'] = False
            data['info'] = '该用户名已被占用'
        else:
            data['status'] = True
            Handle.userlist[self.user] = data['username']
            Handle.usernames.append(data['username'])
            self.user.username = data['username']
            self.refresh_list(data)
            time.sleep(0.1)
        self.send_socket_to_self(data)

    def refresh_list(self, data):
        """刷新在线用户列表"""
        nameList = Handle.usernames
        data["list"] = nameList
        self.send_socket_to_all(data)

    def init_list(self, data):
        """获取在线用户列表"""
        data["type"] = 'login'
        nameList = Handle.usernames
        data["list"] = nameList
        self.send_socket_to_self(data)

    def group_chat(self, data):
        """群聊"""
        self.send_socket_to_all(data)

    def private_chat(self, data):
        """私聊"""
        send_to_namelist = data['to']
        send_to_userlist = get_keys(Handle.userlist, send_to_namelist)
        self.send_socket_to_users(send_to_userlist, data)

    def create_group_chat(self, data):
        """创建的群聊聊天"""
        send_to_namelist = data['to_list']
        print(send_to_namelist)
        send_to_userlist = []
        for username in send_to_namelist[data['group_name']]:
            print(username)
            send_to_userlist += get_keys(Handle.userlist, username)
        self.send_socket_to_users(send_to_userlist, data)

    def create_group(self, data):
        """用户创建了群聊"""
        group_dic = data['group']
        print(group_dic)
        print(data['group_name'])
        group_member_list = []
        send_to_userlist = []
        for username in group_dic[data['group_name']]:
            print(username)
            group_member_list += username
            send_to_userlist += get_keys(Handle.userlist, username)
            try:
                grouplist[username].update(group_dic)
            except:
                grouplist[username] = group_dic
        print(grouplist)
        print(send_to_userlist)
        self.send_socket_to_users(send_to_userlist, data)


    def send_pic_to_all(self, filepath, username):
        """群聊图片"""
        data = {'type': 'group_pic', 'username': username}
        for user in Handle.userlist:
            print(user)
            self.send_socket_to_user(user, data)
            time.sleep(0.1)
            message = 'group_pic '
            user.tcpCliSock.send(message.encode())
            time.sleep(0.1)
            print('Start uploading image!')
            print('Waiting.......')
            print(filepath)
            with open(filepath + '.png', 'rb') as f:
                while True:
                    send_data = f.read(BUFFSIZE)
                    print(send_data)
                    if not send_data:
                        break
                    user.tcpCliSock.send(send_data)
                time.sleep(0.1)  # 延时确保文件发送完整
                user.tcpCliSock.send('EOF'.encode())
                print('Upload completed')
                time.sleep(0.1)
            f.close()
            user.tcpCliSock.send('quit'.encode())
            time.sleep(0.1)
            # data = {'type': 'group_pic_done', 'username': username}
            # self.send_socket_to_user(user, data)
            # time.sleep(0.1)

    def send_file_to_all(self, filepath, username, name):
        """群聊文件"""
        data = {'type': 'group_file', 'username': username, 'filename': name}
        for user in Handle.userlist:
            print(user)
            self.send_socket_to_user(user, data)
            time.sleep(0.1)
            message = 'group_pic '
            user.tcpCliSock.send(message.encode())
            time.sleep(0.1)
            print('Start uploading file!')
            print('Waiting.......')
            print(filepath)
            with open(filepath, 'rb') as f:
                while True:
                    send_data = f.read(BUFFSIZE)
                    print(send_data)
                    if not send_data:
                        break
                    user.tcpCliSock.send(send_data)
                time.sleep(0.1)  # 延时确保文件发送完整
                user.tcpCliSock.send('EOF'.encode())
                print('Upload completed')
                time.sleep(0.1)
            f.close()
            user.tcpCliSock.send('quit'.encode())
            time.sleep(0.1)

    @staticmethod
    def send_socket_to_user(user, data):
        """向用户发送信息包"""
        json_data = json.dumps(data)
        json_data = str.encode(json_data)
        user.tcpCliSock.send(json_data)
        print("Send to users: " + str(json_data))

    @staticmethod
    def send_socket_to_users(send_to_userlist, data):
        """向用户列表发送信息包"""
        json_data = json.dumps(data)
        json_data = str.encode(json_data)
        for user in send_to_userlist:
            user.tcpCliSock.send(json_data)
        print("Send to users: " + str(json_data))

    @staticmethod
    def send_socket_to_all(data):
        """给所有用户发送信息包"""
        userlist = [user for user in Handle.userlist]
        json_data = json.dumps(data)
        json_data = str.encode(json_data)
        for user in userlist:
            user.tcpCliSock.send(json_data)
        print("Send to all users: " + str(json_data))

    def send_socket_to_self(self, data):
        """给本用户发送信息包"""
        json_data = json.dumps(data)
        json_data = str.encode(json_data)
        self.user.tcpCliSock.send(json_data)
        print('Send to user self: ' + str(json_data))

    @staticmethod
    def remove_user(user):
        try:
            handle = Handle(user)
            Handle.userlist.pop(user)
            Handle.usernames.remove(user.username)
            data = {"type": "remove_user", "username": user.username}
            handle.refresh_list(data)
        except Exception as err:
            print(err)

    def recv_pic(self, socket, filepath):
        print('Start saving!')
        with open(filepath+'.png', 'wb+') as f:
            while True:
                data = socket.recv(BUFFSIZE)
                if data == 'EOF'.encode():
                    print('Saving completed!')
                    break
                f.write(data)
        f.close()
        time.sleep(0.1)

    def recv_file(self, socket, filepath):
        print('Start saving!')
        with open(filepath, 'wb+') as f:
            while True:
                data = socket.recv(BUFFSIZE)
                if data == 'EOF'.encode():
                    print('Saving completed!')
                    break
                f.write(data)
        f.close()
        time.sleep(0.1)

    def __main__(self, data):
        """处理信息包"""
        type = data["type"]
        switch = {
            "login": self.login,
            "init_list": self.init_list,
            "group_chat": self.group_chat,
            "private_chat": self.private_chat,
            "create_group": self.create_group,
            "create_group_chat": self.create_group_chat,
        }
        try:
            switch[type](data)
        except Exception as e:
            print(e)
            data["status"] = False
            data["info"] = "未知错误"
            return data


class ClientThread(threading.Thread):
    def __init__(self, user):
        threading.Thread.__init__(self)
        self.user = user

    def run(self):
        handle = Handle(self.user)  # handle input
        try:
            while True:
                json_data = self.user.tcpCliSock.recv(BUFFSIZE)
                data = json.loads(json_data, strict=False)
                print("receive data from: " + data['username'])
                sender = data['username']
                if data['type'] == 'logout':
                    break
                elif data['type'] == 'group_pic':
                    name = str(uuid.uuid1())  # 获取文件名
                    filepath = image_fold_path + name  # 将文件夹和图片名连接起来
                    while True:
                        data = self.user.tcpCliSock.recv(BUFFSIZE)
                        data = data.decode()
                        print("begin receive picture")
                        if data == 'quit':
                            break
                        handle.recv_pic(self.user.tcpCliSock, filepath)
                    handle.send_pic_to_all(filepath, sender)
                elif data['type'] == 'group_file':
                    name = data['filename']  # 获取文件名
                    filepath = file_fold_path + name  # 将文件夹和文件名连接起来
                    while True:
                        data = self.user.tcpCliSock.recv(BUFFSIZE)
                        data = data.decode()
                        print("begin receive file")
                        if data == 'quit':
                            break
                        handle.recv_file(self.user.tcpCliSock, filepath)
                    handle.send_file_to_all(filepath, sender, name)
                else:
                    handle.__main__(data)
        except Exception as err:
            print("连接中断")
            print(err)
        finally:
            name = Handle.userlist[self.user]
            print(str(name) + "退出聊天室")
            Handle.remove_user(self.user)
            self.user.tcpCliSock.close()

    def stop(self):
        try:
            self.user.tcpCliSock.shutdown(2)
            self.user.tcpCliSock.close()
        except Exception as err:
            print("连接中断")
            print(err)


class ChatServer:
    def __main__(self):
        tcpSerSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        tcpSerSock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)  # 在绑定前调用setsockopt让套接字允许地址重用
        tcpSerSock.bind(ADDR)
        tcpSerSock.listen(5)

        threads = []

        while True:
            try:
                print('Waiting for connection...')
                tcpCliSock, addr = tcpSerSock.accept()
                print('...connected from:', addr)

                user = User(addr, tcpCliSock)
                clientThread = ClientThread(user)
                threads += [clientThread]
                clientThread.start()
            except KeyboardInterrupt:
                print('KeyboardInterrupt:')
                for t in threads:
                    t.stop()
                break

        tcpSerSock.close()


if __name__ == '__main__':
    print("\t\tChat Room Server\n")

    server = ChatServer()
    server.__main__()
