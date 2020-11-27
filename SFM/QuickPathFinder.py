import SFM.BasicClasses
import math
import ctypes
import time
import platform

class Node:
    def __init__(self, box, x, y, id):
        self.f = None
        self.g = None
        self.h = None
        self.parent = None
        self.next = None
        self.box = box
        self.occupied = False
        self.x = x
        self.y = y
        self.id = id
        self.closed = False
        self.open = False


class JPSPathFinder:
    def __init__(self, scene):
        self.scene = scene
        self.nodes = None
        self.grid = None
        self.start = None
        self.goal = None
        self.scale_factor = 1 # 路径搜索所用的格子长度为1m/scale_factor。
        self.build_nodes()
        self.node_list = [self.nodes[i][j] for i in range(len(self.nodes)) for j in range(len(self.nodes[0]))]
        self.build_grid()
        if platform.system() == 'Windows':
            libpathfinder = ctypes.CDLL('lib\libpathfinder.dll')
        elif platform.system() == 'Linux':
            libpathfinder = ctypes.CDLL('lib/libpathfinder.so')
        else:
            print('Unsupported platform')
            exit(-1)
        self.direction = libpathfinder.get_direction

    def build_nodes(self):
        """调用此方法来读取场景，初始化AStarPathFinder"""
        x_max = math.ceil(self.scene.border.x) * self.scale_factor
        y_max = math.ceil(self.scene.border.y) * self.scale_factor
        self.nodes = []
        for i in range(0, x_max):
            list = []
            self.nodes.append(list)
            for j in range(0, y_max):
                box = SFM.BasicClasses.Box(i, j, i + 1, j + 1)
                box.scale(1/self.scale_factor)
                node = Node(box, i, j, j + i * y_max)
                list.append(node)
        for box in self.scene.boxes:
            x_max = round(box.p2.x * self.scale_factor)
            x_min = int(box.p1.x * self.scale_factor)
            y_max = round(box.p2.y * self.scale_factor)
            y_min = int(box.p1.y * self.scale_factor)
            for x in range(x_min, x_max):
                for y in range(y_min, y_max):
                    node = self.nodes[x][y]
                    if box.is_intersect(node.box):
                        node.occupied = True

    def build_grid(self):
        grid = (ctypes.c_int * len(self.node_list))() # 1D array
        for i in range(len(self.node_list)):
            node = self.node_list[i]
            if node.occupied:
                grid[i] = 1
            else:
                grid[i] = 0
        self.grid = grid

    def get_node(self, pos):
        x = int(pos.x * self.scale_factor)
        y = int(pos.y * self.scale_factor)
        xs = (0, 0, 1, -1, 1, -1, 0, 1, -1)
        ys = (0, -1, -1, 0, 0, 1, 1, 1, -1)
        for i, j in zip(xs, ys):
            nx = x + i
            ny = y + j
            if not (0 <= nx < len(self.nodes) and 0 <= ny < len(self.nodes[0])):
                continue
            node = self.nodes[nx][ny]
            if node.box.is_in(pos):
                return node
        return None


def path_finder_init(scene):
    global qpf
    qpf = JPSPathFinder(scene)

def get_direction(scene, source):
    """ 寻找路径，获得下一步运动的方向
        scene是Scene类型，source是行人（Circle类型）
        :return: 返回期望方向e，类型为Vector2D，要求e是单位向量e.x^2 + e.y^2 = 1
    """
    global qpf

    start = qpf.get_node(source.pos)
    d = scene.dests[0]
    dest = SFM.BasicClasses.Vector2D(d.p1.x, d.p1.y)
    goal = qpf.get_node(dest)
    if start is None: # 出界
        return SFM.BasicClasses.Vector2D(0, 0)

    ex = ctypes.c_double(0.0)
    ey = ctypes.c_double(0.0)
    qpf.direction(qpf.grid, len(qpf.nodes), len(qpf.nodes[0]), start.x, start.y, goal.x, goal.y, ctypes.byref(ex), ctypes.byref(ey))
    return SFM.BasicClasses.Vector2D(ex.value, ey.value)
