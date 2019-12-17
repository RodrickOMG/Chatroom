import socket
import threading
import json
import time
import base64
import uuid
from tkinter import *
from tkinter import filedialog
from tkmacosx import Button
from PIL import Image, ImageTk
from signal import signal, SIGPIPE, SIG_DFL

signal(SIGPIPE,SIG_DFL)

HOST = '127.0.0.1'  # 主机地址
PORT = 8888  # 端口号
BUFFSIZE = 1024  # 缓存区大小，单位是字节，这里设定了2K的缓冲区
ADDR = (HOST, PORT)  # 链接地址
count = 0
userlist = {}
grouplist = {}
image_fold_path = '/Users/rodrick/Documents/python/Chatroom/temp/img'


class Client:
    def __init__(self):
        self.tcpCliSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.isConnect = False

    def connect(self):
        """连接服务器"""
        if not self.isConnect:
            self.tcpCliSock.connect(ADDR)
            self.isConnect = True
            print("连接成功")
        else:
            print("已经连接，不再重新连接")

    def relogin(self):
        """重新加入聊天室"""
        self.tcpCliSock.close()
        self.__init__()

    def disconnect(self):
        """断开服务器"""
        self.tcpCliSock.close()

    @staticmethod
    def error_msg(info):
        """错误提示界面"""
        errtk = Tk()
        errtk.geometry('250x120')
        errtk.title("错误")
        frame = Frame(errtk, bg='#3C3F41')
        frame.pack(expand=YES, fill=BOTH)
        Label(frame, bg='#3C3F41', fg='#00FA92', text=info).pack(padx=5, pady=20, fill='x')
        bt = Button(frame, text="确定", bg='#3C3F41', fg='#00FA92', command=errtk.destroy).pack()
        errtk.mainloop()

    class Login:
        """登录界面"""

        def __init__(self, parent):
            self.parent = parent

        def login(self, entry, login_window):
            """登录"""
            username = entry.get()
            if username == "":
                self.parent.error_msg("用户名不能为空")
                return False
            self.parent.username = username
            try:
                data = {"type": "login", "username": username}
                json_data = json.dumps(data)
                self.parent.connect()
            except Exception as err:
                print(err)
                self.parent.error_msg("网络连接异常，无法连接到聊天室")
                return False
            else:
                sock = self.parent.tcpCliSock
                json_data = str.encode(json_data)
                sock.send(json_data)
                print('__send__' + str(json_data))
                receive_json_data = sock.recv(BUFFSIZE)
                receive_data = json.loads(receive_json_data, strict=False)
                if receive_data["type"] == "login" and receive_data["username"] == username and \
                        receive_data["status"] == True:
                    # login success!
                    print("进入聊天室成功")
                    main_chat = self.parent.MainChat(self.parent, username)
                    login_window.destroy()
                    main_chat.__main__()
                elif receive_data["type"] == "login" and receive_data["username"] == username \
                        and receive_data["info"] == "该用户名已被占用":
                    self.parent.relogin()
                    self.parent.error_msg("该用户名已被占用")

        def login_window(self):
            """登录窗口"""
            tk = Tk()
            tk.geometry('350x200')
            tk.title('登录')
            frame = Frame(tk, bg='#3C3F41')
            frame.pack(expand=YES, fill=BOTH)
            Label(frame, bg='#3C3F41', fg="#00FA92", font="Arial, 15", text="请输入用户名：", anchor='w').pack(padx=20, pady=15, fill='x')
            entry = Entry(frame, highlightthickness=0, highlightbackground='black', bg='#2B2B2B', fg='#00FA92', insertbackground='#00FA92', width=50, relief='flat')
            entry.pack(padx=10, fill='x')
            entry.bind("<Key-Return>", lambda x: self.login(entry, tk))
            button = Button(frame, font="Arial, 15", bg='#3C3F41', fg='#00FA92', text="加入聊天室", command=lambda: self.login(entry, tk))
            button.pack(pady=40)

            tk.mainloop()

        def __main__(self):
            # 建立窗口
            self.login_window()

    class MainChat:
        """聊天室主窗口"""

        def __init__(self, parent, username):
            self.parent = parent
            self.socket = parent.tcpCliSock
            self.username = username

        class MainWindow:
            def __init__(self, parent):
                self.parent = parent

            def main_window(self):
                """聊天室主窗口"""
                parent = self.parent
                tk = Tk()
                tk.geometry('600x450')
                tk.title('Chat Room')

                # 主背景
                f = Frame(tk, bg='#3C3F41', width=600, height=450)
                f.place(x=0, y=0)

                # 欢迎语
                text = StringVar()
                text.set("欢迎来到聊天室, " + self.parent.username)
                Label(f, fg="#00FA92", bg='#3C3F41', font="Courier, 14", textvariable=text).place(x=170, y=10, anchor=NW)

                # 聊天的内容框
                text_area = Text(f, highlightthickness=0, bg='#2B2B2B', fg="#00FA92", insertbackground='#00FA92', width=60, height=22, bd=0)
                text_area.place(x=12, y=40, anchor=NW)
                text_area.bind("<KeyPress>", lambda x: "break")
                parent.text_area = text_area

                # 右侧联系人选单
                Label(f, fg="#00FA92", text="联系人:", bg="#3C3F41").place(x=455, y=10, anchor=NW)
                listbox = Listbox(f, width=13, height=13, bg='#2B2B2B', fg="#00FA92")
                listbox.place(x=460, y=40, anchor=NW)
                parent.listbox = listbox

                # 创建群聊
                bt_create_group = Button(f, bg='#3C3F41', fg='#D636D2', width=100, text="创建多人聊天", font="Arial, 12", command=lambda: self.create_group_window())
                bt_create_group.place(x=520, y=290, anchor=CENTER)

                bt_clear = Button(f, bg='#3C3F41', fg='#DBBF6C', width=50, text="清屏", command=lambda: text_area.delete(0.0, END))
                bt_clear.place(x=560, y=365, anchor=CENTER)

                bt_pic = Button(f, bg='#3C3F41', fg='#D636D2', width=55, text="图片", font="Arial, 14", command=lambda: self.picture(parent.socket, chat_name))
                bt_pic.place(x=110, y=405, anchor=CENTER)

                bt_file = Button(f, bg='#3C3F41', fg='#D636D2', width=55, text="文件", font="Arial, 14", command=lambda: self.send(parent.socket, chat_name, et_input))
                bt_file.place(x=180, y=405, anchor=CENTER)

                # 下方内容输入
                chat_name = Label(f, fg="#00FA92", text="群聊", font="Arial, 12", bg='#2B2B2B', width=8)
                chat_name.place(x=12, y=352)
                listbox.bind('<Double-Button-1>', lambda x: self.change_send_to(listbox, chat_name))
                self.chat_name = chat_name

                # 输入要发送的消息
                et_input = Entry(f, highlightthickness=0, highlightbackground='black', width=37, bg='#2B2B2B', fg='#00FA92', insertbackground='#00FA92', borderwidth=0)
                et_input.place(x=90, y=355)
                et_input.bind('<Key-Return>', lambda x: self.send(parent.socket, chat_name, et_input))
                self.et_input = et_input

                # 发送消息
                bt_send = Button(f, bg='#3C3F41', fg='#4FB6F9', width=50, text="发送", command=lambda: self.send(parent.socket, chat_name, et_input))
                bt_send.place(x=480, y=365, anchor=CENTER)

                tk.mainloop()

            def create_group_window(self):
                """创建多人聊天"""
                parent = self.parent
                tk = Tk()
                tk.geometry('200x300')
                tk.title('创建多人聊天')

                f = Frame(tk, bg='#3C3F41', width=200, height=300)
                f.place(x=0, y=0)

                listbox = Listbox(f, width=200, height=200, bg='#2B2B2B', fg="#00FA92", selectmode=MULTIPLE)
                listbox.place(x=0, y=0, anchor=NW)
                for l in userlist.keys():
                    listbox.insert(END, l)
                listbox.pack()

                bt_confirm = Button(f, bg='#3C3F41', fg='#DBBF6C', width=50, text="确定", command=lambda: self.group_name(listbox, tk))
                bt_confirm.place(x=50, y=265, anchor=CENTER)

                bt_cancel = Button(f, bg='#3C3F41', fg='#DBBF6C', width=50, text="取消", command=tk.destroy)
                bt_cancel.place(x=140, y=265, anchor=CENTER)

                tk.mainloop()

            def group_name(self, listbox, parent_tk):
                """输入群聊名称"""
                tk = Tk()
                tk.geometry('350x200')
                tk.title('输入群聊名称')
                frame = Frame(tk, bg='#3C3F41')
                frame.pack(expand=YES, fill=BOTH)
                Label(frame, bg='#3C3F41', fg="#00FA92", font="Arial, 13", text="请输入群聊名称：", anchor='w').pack(padx=20,
                                                                                                            pady=15,
                                                                                                            fill='x')
                entry = Entry(frame, highlightthickness=0, highlightbackground='black', bg='#2B2B2B', fg='#00FA92',
                              insertbackground='#00FA92', width=50, relief='flat')
                entry.pack(padx=10, fill='x')
                entry.bind("<Key-Return>", lambda x: self.create_group(entry, tk, listbox, parent_tk))
                button = Button(frame, font="Arial, 13", bg='#3C3F41', fg='#00FA92', text="创建群聊",
                                command=lambda: self.create_group(entry, tk, listbox, parent_tk))
                button.pack(pady=40)

                tk.mainloop()

            def change_send_to(self, listbox, chat_name):
                """双击选择聊天对象"""
                try:
                    if self.parent.username != listbox.get(listbox.curselection()):
                        chat_name['text'] = listbox.get(listbox.curselection())
                except Exception as err:
                    print(err)
                    pass  # nothing choose

            def create_group(self, entry, tk, listbox, parent_tk):
                group_name = entry.get()
                group_namelist = [self.parent.username]
                send_grouplist = {}
                try:
                    index_list = listbox.curselection()
                    if group_name == "":
                        group_name = self.parent.username
                        for index in range(len(index_list)):
                            print(index)
                            group_name += '、' + listbox.get(index)
                            group_namelist.append(listbox.get(index))
                        group_name += '的群聊'

                    else:
                        if group_name not in grouplist:
                            for index in range(len(index_list)):
                                group_namelist.append(listbox.get(index))
                        else:
                            self.parent.parent.error_msg("该群聊名称已存在")
                            return False
                    grouplist[group_name] = group_namelist
                    send_grouplist[group_name] = group_namelist
                    tk.destroy()
                    parent_tk.destroy()
                except:
                    self.parent.parent.error_msg("未选中任何联系人")
                data = {'type': 'create_group', 'group': send_grouplist, 'username': self.parent.username}
                json_data = json.dumps(data)
                json_data = str.encode(json_data)
                self.parent.socket.send(json_data)
                print('__send__' + str(json_data))
                print(group_name)
                print(group_namelist)
                print(grouplist)

            def picture(self, socket, chat_name):
                filename = filedialog.askopenfilename(title='请选择发送的图片')
                to_user = chat_name['text']
                username = self.parent.username
                flag = 1
                if filename:
                    print(filename)
                    name = filename.split('/')[-1]
                    print(name)
                    image_64 = base64.b64encode(open(filename, "rb").read())
                    image_64 = image_64.decode('ascii')
                    send_data = 0
                    if to_user == '群聊':
                        while flag == 1:
                            if send_data + BUFFSIZE < len(image_64):
                                print(image_64[send_data:send_data+BUFFSIZE-1])
                                send_image_64 = image_64[send_data:send_data + BUFFSIZE-1]
                                data = {'type': 'group_pic', 'image_64': send_image_64,
                                        'username': username, 'end': 'False', 'pic_size': len(image_64)}
                                send_data += BUFFSIZE
                            else:
                                send_image_64 = image_64[send_data:len(image_64)-1]
                                data = {'type': 'group_pic', 'image_64': send_image_64,
                                        'username': username, 'end': 'True', 'pic_size': len(image_64)}
                                flag = 0
                            json_data = json.dumps(data)
                            json_data = str.encode(json_data)
                            socket.send(json_data)
                            print('__send__' + str(json_data))
                            time.sleep(0.1)
                    else:
                        data = {'type': 'private_pic', 'image_64': image_64, 'to': to_user, 'username': username}
                        pic = Image.open(filename)
                        self.parent.pic_to_insert = ImageTk.PhotoImage(pic)
                        text_area = self.parent.text_area
                        t = "[" + to_user + ']'
                        text_area.insert(END, t)
                        text_area.image_create(END, image=self.parent.pic_to_insert)

            def send(self, socket, chat_name, et_input):
                """点击发送按钮"""
                text = et_input.get()
                if text != "":  # 发送消息不能为空
                    to_user = chat_name['text']
                    username = self.parent.username
                    print(to_user)
                    if to_user == '群聊':
                        data = {'type': 'group_chat', 'msg': text, 'username': username}
                    elif to_user == '组播':
                        return
                    else:
                        # 私聊
                        data = {'type': 'private_chat', 'msg': text, 'to': to_user, 'username': username}
                        text_area = self.parent.text_area
                        t = "[" + to_user + ']' + text + '\n'
                        text_area.insert(END, t)
                    json_data = json.dumps(data)
                    json_data = str.encode(json_data)
                    socket.send(json_data)
                    print('__send__' + str(json_data))
                    et_input.delete(0, END)

        class ListenThread(threading.Thread):
            """Socket监听线程，对收到的信息作出相应反馈"""

            def __init__(self, socket, parent):
                threading.Thread.__init__(self)
                self.parent = parent
                self.socket = socket
                self.recvd_size = 0
                self.recvd_pic = ''

            def run(self):
                while True:
                    try:
                        receive_json_data = self.socket.recv(BUFFSIZE)
                        receive_data = json.loads(receive_json_data, strict=False)
                    except Exception as err:
                        print(err)
                        break
                    print("receive data: " + str(receive_data))
                    switch = {
                        "login": self.list,
                        "remove_user": self.list,
                        "group_chat": self.chat,
                        "private_chat": self.chat,
                        "group_pic": self.pic,
                        "pong": self.pong
                    }
                    switch[receive_data['type']](receive_data)
                print("与服务器断开连接")

            def list(self, data):
                """刷新列表"""
                global count, userlist
                if data['type'] == 'login' and count < 1:
                    time.sleep(0.1)
                    if count == 0:
                        text_area = self.parent.text_area
                        text = (data['username'] + "加入聊天室\n")
                        text_area.insert(END, text)
                        userlist[data['username']] = {}
                    data['type'] = 'init_list'
                    json_data = json.dumps(data)
                    json_data = str.encode(json_data)
                    self.socket.send(json_data)
                    print('send data: ' + str(json_data))
                    count += 1
                elif data['type'] == 'remove_user':
                    text_area = self.parent.text_area
                    text = (data['username'] + "退出聊天室\n")
                    text_area.insert(END, text)
                else:
                    count = 0
                    listbox = self.parent.listbox
                    list = ['群聊', '组播']
                    list += data['list']
                    listbox.delete(0, END)  # 清空现有列表
                    userlist.clear()
                    for l in list:
                        listbox.insert(END, l)  # 插入新列表
                        if str(l) != '群聊' and str(l) != '组播' and str(l) != self.parent.username:
                            userlist[l] = {}

            def chat(self, data):
                """接收聊天信息并打印"""
                text_area = self.parent.text_area
                if data ['type'] == 'group_chat':
                    text = ('[群聊]' + data['username'] + ': ' + data['msg'] + '\n')
                else:
                    text = ('[' + data['username'] + ']' + data['username'] + ': ' + data['msg'] + '\n')
                text_area.insert(END, text)

            def pic(self, data):
                """接收图片并打印"""
                text_area = self.parent.text_area
                pic_size = data['pic_size']
                self.recvd_pic += data['image_64']
                self.recvd_size += BUFFSIZE
                if self.recvd_size == pic_size and data['end'] == 'True':
                    image_data = base64.b64decode(self.recvd_pic)
                    image_name = str(uuid.uuid1())
                    image_name += '.jpg'
                    file = open(image_fold_path + image_name, 'wb')
                    file.write(image_data)
                    file.close()
                    if data['type'] == 'group_pic':
                        text = ('[群聊]' + data['username'] + ': ')
                    text_area.insert(END, text)
                    pic = Image.open(image_fold_path + image_name)
                    self.parent.pic_to_insert = ImageTk.PhotoImage(pic)
                    text_area.image_create(END, image=self.parent.pic_to_insert)
                    self.recvd_pic = ''
                    self.recvd_size = 0

            def pong(self, data):
                """ping pong!"""
                textArea = self.parent.textArea
                text = '[Server]pong\n'
                textArea.insert(END, text)

        def __main__(self):
            # 开启监听线程
            listenThread = self.ListenThread(self.socket, self)
            listenThread.daemon = True
            listenThread.start()
            self.listenThread = listenThread

            window = self.MainWindow(self)
            window.main_window()
            self.window = window

    def __main__(self):
        login = Client.Login(self)
        login.__main__()


if __name__ == '__main__':
    client = Client()
    client.__main__()
