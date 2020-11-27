# coding=utf-8

import math
import time
import threading
import copy
import ctypes
import inspect

import tkinter

from SFM import BasicClasses


MAX_X = 500
MAX_Y = 500
MAX_COLOR = 50
CANVAS_BG = "white"
default_path = "D://save.p"
TIME_STEP = BasicClasses.get_time_step()


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)
    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")
    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


class SfmGui:
    def __init__(self, scene, epoch):
        self.epoch = epoch
        self.timeNow = 0

        self.color_list = []
        self.color_list_init(MAX_COLOR)
        self.click_coordinate = {"x": -1, "y": -1, "box": None}
        self.boxes = []  # 障碍物
        self.dests = []  # 目标位置
        self.peds = []  # 当前所有人的位置，是一个列表
        self.pre_peds = None

        self.default_scene = copy.deepcopy(scene)
        self.scene = scene
        self.root = tkinter.Tk()
        self.root.resizable(False, False)
        self.root.title("社会力模型仿真")

        self.timeNowStr = tkinter.StringVar(self.root)
        self.remainPeople = tkinter.StringVar(self.root)

        self.canvas = tkinter.Canvas(self.root, bg=CANVAS_BG, width=MAX_X + 50, height=MAX_Y + 50)

        self.canvas.pack(side=tkinter.LEFT)
        self.change_scene(scene)

        # 实现界面右边的功能 D:\0bianchen\python\图形编程\save.p
        self.frame = tkinter.Frame(self.root)
        self.frame.pack(side=tkinter.RIGHT)
        self.the_path = tkinter.Entry(self.frame, width=30)
        self.bind_btn()
        self.th = None

    def begin_simulate(self):
        steps_per_frame = 12
        steps_cnt = 0
        while self.scene.peds_arrived() != len(self.peds):
            # time.sleep(TIME_STEP)
            steps_cnt += 1
            self.timeNow = self.timeNow + TIME_STEP
            self.timeNowStr.set("%.4f" % self.timeNow)
            self.remainPeople.set(len(self.peds) - self.scene.peds_arrived())
            try:
                self.scene.update()
            except IndexError:
                print("IndexError\n\n")
                exit(0)
            if steps_cnt < steps_per_frame:
                continue
            steps_cnt = 0
            i = 0
            for ped in self.peds:
                x = ped[0].pos.get_x()
                y = ped[0].pos.get_y()
                # print(x, y)
                r = ped[0].get_radius()
                self.canvas.coords(ped[1], (x - r, y - r, x + r, y + r))
                if self.pre_peds:
                    pre_x = self.pre_peds[i][0].pos.get_x()
                    pre_y = self.pre_peds[i][0].pos.get_y()
                    self.canvas.create_line(x, y, pre_x, pre_y, fill=self.get_color(i + 10))
                i += 1
            #self.pre_peds = copy.deepcopy(self.peds)

    def begin_simulate_btn(self, event):
        if self.th and self.th.isAlive():
            stop_thread(self.th)
            self.th = None
        self.th = threading.Thread(target=self.begin_simulate, args=())
        self.th.setDaemon(True)
        self.th.start()

    def color_list_init(self, num):
        n = int(256 / int(math.pow(num, 1 / 3) + 1))
        for i in range(0, 256, n):
            for j in range(0, 256, n):
                for k in range(0, 256, n):
                    self.color_list.append("#%02x%02x%02x" % (i, j, k))

    def get_color(self, index):
        return self.color_list[index % len(self.color_list)]

    def get_click(self, event):
        # 在此函数中获取点击的位置信息，判断出是哪个元素被点击
        # print("clicked at ", event.x, event.y)
        x_now = event.x
        y_now = event.y
        for box in self.boxes:
            x0 = box[0].p1.get_x()
            y0 = box[0].p1.get_y()
            x1 = box[0].p2.get_x()
            y1 = box[0].p2.get_y()
            if ((x_now < x0) ^ (x_now < x1)) & ((y_now < y0) ^ (y_now < y1)):
                # print("true")
                self.click_coordinate['x'] = x_now
                self.click_coordinate['y'] = y_now
                self.click_coordinate['box'] = box
                return
        for box in self.dests:
            x0 = box[0].p1.get_x()
            y0 = box[0].p1.get_y()
            x1 = box[0].p2.get_x()
            y1 = box[0].p2.get_y()
            if ((x_now < x0) ^ (x_now < x1)) & ((y_now < y0) ^ (y_now < y1)):
                # print("true")
                self.click_coordinate['x'] = x_now
                self.click_coordinate['y'] = y_now
                self.click_coordinate['box'] = box
                return
        self.click_coordinate['x'] = -1
        self.click_coordinate['y'] = -1
        self.click_coordinate['box'] = None

    def click_release(self, event):
        # 画布中鼠标释放时，执行此函数将相应的box移动
        # print("Release at ", event.x, event.y)
        x_now = event.x
        y_now = event.y
        if self.click_coordinate['box']:
            x_change = x_now - self.click_coordinate['x']
            y_change = y_now - self.click_coordinate['y']
            '''
            box = self.click_coordinate['box']
            self.move_box(box, x_change, y_change)
            '''
            self.click_coordinate['box'][0].p1.set_x(x_change + self.click_coordinate['box'][0].p1.get_x())

            self.click_coordinate['box'][0].p2.set_x(x_change + self.click_coordinate['box'][0].p2.get_x())
            self.click_coordinate['box'][0].p1.set_y(y_change + self.click_coordinate['box'][0].p1.get_y())
            self.click_coordinate['box'][0].p2.set_y(y_change + self.click_coordinate['box'][0].p2.get_y())
            self.canvas.move(self.click_coordinate['box'][1], x_change, y_change)
        pass

    def reset_scene(self, event):
        # 重置场景
        self.timeNow = 0
        self.timeNowStr.set("%.4f" % self.timeNow)
        if self.th and self.th.isAlive():
            stop_thread(self.th)
            self.th = None
        scene = copy.deepcopy(self.default_scene)
        self.change_scene(scene)

    def change_scene(self, scene):
        # 改变场景
        self.pre_peds = None
        self.canvas.delete(tkinter.ALL)
        self.scene = scene
        self.boxes = [[x, -1] for x in scene.boxes]  # 障碍物
        self.dests = [[x, -1] for x in scene.dests]  # 目标位置
        self.peds = [[x, -1] for x in scene.peds]  # 当前所有人的位置，是一个列表
        self.init_canvas()
        '''
        boxes = [x[0] for x in self.boxes]
        dests = [x[0] for x in self.dests]
        peds = [x[0] for x in self.peds]
        scene = BasicClasses.Scene(boxes=boxes, peds=peds, dests=dests)
        scene.save(path)
        '''

    def init_canvas(self):
        # 向画布中加入各种元素
        color_sum = len(self.color_list)
        # 将传入的障碍物添加到画布中
        i = 0
        for box in self.boxes:
            # print(get_color(color_sum -1 - i))
            self.add_box(box, fill=self.get_color(color_sum - 1))
            i += 1
        i = 0
        for ped in self.peds:
            # print(get_color(i))
            self.add_person(ped, fill=self.get_color(i + 10))
            i += 1
        i = 0
        for dest in self.dests:
            self.add_dest(dest, fill=self.get_color(0))
            i += 1

    def bind_btn(self):
        # 绑定函数
        tkinter.Label(self.frame, text='仿真时间为 ').pack()
        tkinter.Label(self.frame, textvariable=self.timeNowStr).pack()
        tkinter.Label(self.frame, text='剩余人数为 ').pack()
        tkinter.Label(self.frame, textvariable=self.remainPeople).pack()

        self.canvas.bind("<Button-1>", lambda x: self.get_click(x))
        self.canvas.bind("<ButtonRelease-1>", lambda x: self.click_release(x))

        new_button = tkinter.Button(self.frame, text="开始仿真")
        new_button.bind("<Button-1>", lambda x: self.begin_simulate_btn(x))
        new_button.pack()

        new_button = tkinter.Button(self.frame, text="重置场景")
        new_button.bind("<Button-1>", self.reset_scene)
        new_button.pack()

    def add_box(self, box, fill="black"):
        # 加入障碍物
        # print(self.boxes.index(box))
        x0 = box[0].p1.get_x()
        y0 = box[0].p1.get_y()
        x1 = box[0].p2.get_x()
        y1 = box[0].p2.get_y()
        box[1] = self.canvas.create_polygon(x0, y0, x1, y0, x1, y1, x0, y1, fill=fill)

    def add_person(self, ped, fill="black"):
        # 加入人的信息
        # print(self.boxes.index(box))

        x = ped[0].pos.get_x()
        y = ped[0].pos.get_y()
        r = ped[0].get_radius()
        # r = ped[0].radius * scale_factor
        ped[1] = self.canvas.create_oval((x - r, y - r, x + r, y + r), fill=fill)

    def add_dest(self, dest, fill="black"):
        x0 = dest[0].p1.get_x()
        y0 = dest[0].p1.get_y()
        x1 = dest[0].p2.get_x()
        y1 = dest[0].p2.get_y()
        dest[1] = self.canvas.create_polygon(x0, y0, x1, y0, x1, y1, x0, y1, fill=fill)

    def move_box(self, box, x, y):
        self.canvas.move(box[1], x, y)
        box[0].p1.set_x(x + box[0].p1.get_x())
        box[0].p2.set_x(x + box[0].p2.get_x())
        box[0].p1.set_y(y + box[0].p1.get_y())
        box[0].p2.set_y(y + box[0].p2.get_y())
