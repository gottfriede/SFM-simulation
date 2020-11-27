#!/usr/bin/env python
# coding=utf-8

from GuiModel.Gui import SfmGui
from SFM.Scenes import *
import SFM.QuickPathFinder


if __name__ == '__main__':
    '''
    boxes: 障碍物和墙们，Box类型的列表
    dests: 目标位置们，Box类型的列表，可以包含在boxes中
    peds: 行人们，Circle类型，可以是一个列表
    '''
    scene = get_scene(40)  # 横向障碍物，参数是人数
    SFM.QuickPathFinder.path_finder_init(scene)
    g_gui = SfmGui(scene, 10000)

    g_gui.root.mainloop()