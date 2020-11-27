import random
import math
import numpy as np
import SFM.QuickPathFinder
import pickle
import time

"""
    为了简化，我们对每个行人的参数A(N), B(m), desired_speed(m/s), mass(kg)取相同的值。
    肩宽的一半radius(m)服从U(0.25, 0.35)，也就是肩宽在区间[0.5m, 0.7m]服从均匀分布。
    特征时间ch_time是0.5s
"""
param = {
    'A': 2000.0,
    'B': 0.08,
    'desired_speed': 2.0,
    'mass': 80.0,
    'r_upper': 0.35,
    'r_lower': 0.25,
    'ch_time': 0.5,
    'time_step': 0.005
}


path_finder_test = False


def get_time_step():
    return param['time_step']


def pf_test():
    global path_finder_test
    path_finder_test = True


class Vector2D:
    """ 二维向量，表示力、速度、位置或者方向。
    Attributes:
        x: 横坐标
        y: 纵坐标
    """
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        if isinstance(scalar, (int, float)):
            return Vector2D(self.x * scalar, self.y * scalar)
        else:
            return NotImplemented

    def __rmul__(self, scalar):
        return self * scalar

    def __truediv__(self, scalar):
        if isinstance(scalar, (int, float)):
            return Vector2D(self.x / scalar, self.y / scalar)
        else:
            return NotImplemented

    def norm(self):
        return math.sqrt(self.x ** 2 + self.y ** 2)

    def __str__(self):
        return 'Vector2D(%.2f, %.2f)' % (self.x, self.y)

    def get_x(self):
        return int(self.x * Scene.scale_factor)

    def get_y(self):
        return int(self.y * Scene.scale_factor)

    def set_x(self, x):
        self.x = x / Scene.scale_factor

    def set_y(self, y):
        self.y = y / Scene.scale_factor

    def get_rotate_angle(self):
        """计算这个向量逆时针旋转到(1, 0)的角度，[-pi, pi)
            cosθ=a·b/(|a||b|)
            sinθ=axb/(|a||b|), b = (1, 0)
        """
        angle = math.acos(self.x / self.norm())
        if self.y >= 0:
            angle = -angle
        return angle

    def rotate(self, angle):
        if self.x == 0 or self.y == 0:
            return Vector2D(self.x, self.y)
        else:
            l = self.norm()
            t = math.atan2(self.y, self.x) + angle
            return Vector2D(l * math.cos(t), l * math.sin(t))


class Circle:
    """ Circle表示行人
    Attributes:
        pos: 位置向量
        vel: 当前速度
        next_pos: 下一个位置
        next_vel: 下一时刻速度
        mass: 质量
        radius: 圆的半径，或人肩宽的一半
    """

    def __init__(self, x, y, vx, vy, mass, scene=None):
        self.pos = Vector2D(x, y)
        self.vel = Vector2D(vx, vy)
        self.next_pos = self.pos
        self.next_vel = self.vel
        self.radius = random.uniform(param['r_lower'], param['r_upper'])
        self.mass = mass
        self.scene = scene
        self.arrived = False

    def get_radius(self):
        return self.radius * Scene.scale_factor

    def distance_to(self, other):
        """ 计算与参数other的距离
        根据other的类型（Circle，或墙或障碍物）分别计算
        :return: 距离向量
        """
        if isinstance(other, Circle):
            return self.pos - other.pos
        # else other is instance of Box
        center = other.center()
        dx = max(abs(self.pos.x - center.x) - other.width() / 2, 0)
        dy = max(abs(self.pos.y - center.y) - other.height() / 2, 0)
        if dx > 0 and dy > 0:
            n = Vector2D(np.sign(self.pos.x - center.x) * dx, np.sign(self.pos.y - center.y) * dy)
        elif dx > 0 and dy == 0:
            n = Vector2D(self.pos.x - center.x, 0)
        else:   # dx == 0 and dy > 0
            n = Vector2D(0, self.pos.y - center.y)
        if n.norm() > 0:
            n = n / n.norm()
        return math.sqrt(dx ** 2 + dy ** 2) * n

    def is_intersect(self, other):
        if isinstance(other, Box):
            return self.distance_to(other).norm() < self.radius
        elif isinstance(other, Circle):
            return self.distance_to(other).norm() < self.radius + other.radius

    def ped_repulsive_force(self):
        """ 计算行人与其他行人间的排斥力

        使用公式:
            f_i = ∑(j)f_ij 结果
            f_ij = A * e^((r_ij - d_ij) / B) * n_ij
            r_ij = r_i + r_j 半径之和
            d_ij = ||r_i - r_j|| 圆心距离
            n_ij = (r_i - r_j) / d_ij 单位方向向量

        :return: 其他行人们对此人的合力f_i
        """
        others = list(self.scene.peds)
        others.remove(self)
        force = Vector2D(0.0, 0.0)
        for other in others:
            d_vec = self.distance_to(other)
            d = d_vec.norm()
            n = d_vec / d   # n is a unit vector
            radius_sum = self.radius + other.radius
            force += param['A'] * math.exp((radius_sum - d) / param['B']) * n
        return force

    def wall_repulsive_force(self):
        """ 计算与障碍物或墙的排斥力

        使用公式:
            ∑(W)f_iW 结果
            f_iW = A * e^((ri-diW)/B) * niW
        注意niW是一个向量,niW的方向是由墙指向行人

        :return: 所有墙和障碍物对此人的合力
        """
        force = Vector2D(0.0, 0.0)
        for box in self.scene.boxes:
            d_vec = self.distance_to(box)
            if d_vec.norm() == 0:
                print("撞墙了")
                continue
            n = d_vec / d_vec.norm()    # n is a vector
            force += param['A'] * math.exp((self.radius - d_vec.norm()) / param['B']) * n
        return force

    def desired_force(self):
        """ 计算期望力
        使用公式:
            m * (v * e - vc) / t_c
            m是质量，v是期望速度，e是期望方向(get_direction())
            vc是当前速度，t_c是特征时间
        :return: 期望力
        """
        e = SFM.QuickPathFinder.get_direction(self.scene, self)
        return (param['desired_speed'] * e - self.vel) / param['ch_time'] * self.mass

    def get_force(self):
        """ 计算合力"""
        f1 = self.ped_repulsive_force()
        f2 = self.wall_repulsive_force()
        f3 = self.desired_force()
        if path_finder_test:
            return f3
        return f1 + f2 + f3


    def accleration(self):
        """ 根据合力和质量计算加速度
        :return: 加速度
        """
        acc = self.get_force() / self.mass
        if acc.norm() > 10:
            acc = acc / acc.norm() * 10
        return acc

    def compute_next(self, scene):
        self.scene = scene
        self.next_pos = self.pos + self.vel * param['time_step']
        acc = self.accleration()
        self.next_vel = self.vel + acc * param['time_step']

    def update_status(self):
        """ 更新此人的位置和速度
        Pre-conditions: 首先调用compute_next()
        注意所有的行人应该同时更新位置和速度
        """
        self.pos = self.next_pos
        self.vel = self.next_vel


class Box:
    """ Box表示障碍物或墙(矩形)
    Attributes:
        p1:
        p2: 矩形对角线上的两个点的坐标。
    """

    def __init__(self, x1, y1, x2, y2):
        self.p1 = Vector2D(x1, y1)
        self.p2 = Vector2D(x2, y2)

    def scale(self, factor):
        self.p1 = self.p1 * factor
        self.p2 = self.p2 * factor

    def is_intersect(self, other):
        """other is of instance Box"""
        return self.p2.x > other.p1.x and self.p1.x < other.p2.x and self.p2.y > other.p1.y and self.p1.y < other.p2.y

    def is_in(self, pos):
        return self.p1.x <= pos.x < self.p2.x and self.p1.y <= pos.y <= self.p2.y

    def center(self):
        return (self.p1 + self.p2) / 2

    def width(self):
        return math.fabs(self.p2.x - self.p1.x)

    def height(self):
        return math.fabs(self.p2.y - self.p1.y)

class Scene:
    """ Scene是一个场景，包括静态的墙、障碍物和动态的行人
    Attributes:
        boxes: 障碍物和墙们，Box类型的列表
        dests: 目标位置们，Box类型的列表，可以包含在boxes中
        peds: 行人们，Circle类型，可以是一个列表
    """
    scale_factor = 1

    def __init__(self, dests=None, peds=None, boxes=None):
        self.border = None
        self.dests = dests
        self.peds = peds
        self.boxes = boxes
        self.time_sum = 0
        self.count = 0

    def load(self, path):
        """ 从文件中加载场景
        :param path: 文件路径
        """
        with open(path, "rb") as f:
            read_data = pickle.load(f)
            self.dests = read_data.dests
            self.peds = read_data.peds
            self.boxes = read_data.boxes
            self.border = read_data.border
            self.scale_factor = read_data.scale_factor
            SFM.QuickPathFinder.path_finder_init(self)

    def peds_arrived(self):
        arrived = 0
        for ped in self.peds:
            if ped.arrived:
                arrived = arrived + 1
            if ped.is_intersect(self.dests[0]):
                ped.arrived = True
        return arrived

    def update(self):
        """ 推进一个时间步长，更新行人们的位置"""
        for ped in self.peds:
            ped.compute_next(scene=self)
        for ped in self.peds:
            ped.update_status()


    def save(self, path):
        """ 保存场景到路径path"""
        with open(path, "wb") as f:
            pickle.dump(self, f)
