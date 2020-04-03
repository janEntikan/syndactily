from random import shuffle
from panda3d.core import NodePath
from panda3d.core import CollisionNode, CollisionSphere, CollideMask
from wezupath import NavGraph
from panda3d.core import PStatClient

class Key():
    def __init__(self, map, color, node):
        self.map = map
        self.color = color
        self.node = node
        col = CollisionNode(node.name)
        col.add_solid(CollisionSphere((0,0,0), 1))
        col.set_collide_mask(base.itemmask)
        self.col_node = self.map.collisions.attach_new_node(col)
        self.col_node.set_pos(node.get_pos())
        self.col_node.set_z(node, 1)

    def set(self, item):
        self.node.reparent_to(item)
        self.col_node.reparent_to(item)
        item.wrt_reparent_to(render)
        self.col_node.wrt_reparent_to(self.map.collisions)

    def take(self, who):
        base.sounds2d["key"].play()
        rainbow = list("roygbivw")
        index = rainbow.index(self.color)
        indicator = NodePath("indicates_key_"+self.color)
        self.map.locks[self.color].copy_to(indicator)
        indicator.reparent_to(render2d)
        indicator.set_scale(0.14)
        indicator.set_pos(-0.85+index/4, 0, 1.1)

        who.keys += self.color
        self.node.detach_node()
        self.col_node.detach_node()

class Door():
    def __init__(self, map, node):
        self.map = map
        self.node = node
        self.init_heading = self.node.get_h()
        pos = node.get_pos(render)
        node.set_pos(pos)
        if self.node.get_z() < 2:
            self.node.reparent_to(self.map.doors_node_f1)
        else:
            self.node.reparent_to(self.map.doors_node_f2)
        self.node.set_collide_mask(base.mapmask)
        self.open = False
        self.speed = 5
        self.make_key()
        self.timer = 0
        col = CollisionNode(node.name)
        col.add_solid(CollisionSphere((0,0,0), 1.5))
        col.set_collide_mask(base.itemmask)
        col_node = self.map.collisions.attach_new_node(col)
        col_node.set_pos(node.get_pos(render))
        col_node.set_y(node, 2)
        self.opening = False

    def make_key(self):
        if self.node.name == "door.000":
            self.lock = "w"
            return
        door_number = self.node.name[-4:]
        item = self.map.model.find("**/item"+door_number)
        self.lock = self.node.get_tag("lock")
        if self.lock and self.map.initkey:
            if len(self.map.colors) > 1:
                lock_color = self.map.colors[0]
                self.lock = lock_color
                lock = self.map.model.find("**/lock"+door_number)
                self.map.locks[lock_color].copy_to(lock)
                lock.wrt_reparent_to(self.map.locks_node)
                self.map.colors = self.map.colors[1:]
                key_color = self.map.colors[0]
                item = self.map.model.find("**/item"+door_number)
                self.map.keys[key_color].set(item)
            else:
                self.lock = None
        else:
            self.lock = None
        if not self.map.initkey and not self.lock:
            item = self.map.model.find("**/item"+door_number)
            if item:
                self.map.initkey = True
                self.map.keys["r"].set(item)
                return

    def update(self):
        if self.open:
            if not self.opening:
                base.audio3d.attachSoundToObject(base.sounds3d["door_open"], self.node)
                base.sounds3d["door_open"].play()
                base.sounds3d["door_open"].set_volume(1)
                self.opening = True
            self.timer = 1
            self.node.reparent_to(render)
            if self.node.get_h() > self.init_heading-90:
                self.node.set_h(self.node.get_h()-self.speed)
        elif self.timer > 0:
            self.timer -= base.dt
        elif self.node.get_h() < self.init_heading:
            if self.opening:
                base.audio3d.attachSoundToObject(base.sounds3d["door_closed"], self.node)
                base.sounds3d["door_closed"].play()
                base.sounds3d["door_closed"].set_volume(1)
                self.opening = False
            self.node.set_h(self.node.get_h()+self.speed)
        else:
            if self.node.get_z() < 2:
                self.node.reparent_to(self.map.doors_node_f1)
            else:
                self.node.reparent_to(self.map.doors_node_f2)
        self.open = False


class Map():
    def __init__(self, filename):
        self.model = loader.loadModel("models/roem.bam")
        self.model.reparent_to(render)

        self.navigation_mesh = self.model.find("navigation_mesh")
        self.navigation_mesh.hide()
        self.navigation_mesh.detach_node()
        self.navigation_graph = NavGraph(self.navigation_mesh)

        self.collisions = render.attach_new_node("collisions")
        collision_mesh = self.model.find("collision_mesh")
        collision_mesh.reparent_to(self.collisions)
        collision_mesh.hide()
        collision_mesh.set_collide_mask(base.mapmask)

        self.locks_node = render.attachNewNode("all_door_locks")
        self.keys = {}
        self.locks = {}
        keys_model = loader.load_model("models/key.bam")
        for l, lock_node in enumerate(keys_model.find_all_matches("**/lock_*")):
            color = lock_node.name[-1:]
            self.locks[color] = lock_node
        for key_node in keys_model.find_all_matches("**/key_*"):
            color = key_node.name[-1:]
            self.keys[color] = Key(self, color, key_node)

        self.colors = "roygbivw"
        self.initkey = False
        self.doors = {}
        self.doors_node = self.collisions.attach_new_node("all_doors")
        self.doors_node_f1 = self.collisions.attach_new_node("all_doors_f1")
        self.doors_node_f2 = self.collisions.attach_new_node("all_doors_f2")

        doors = list(self.model.find_all_matches("**/door*"))
        shuffle(doors)
        shuffle(doors)
        shuffle(doors)

        for door in doors:
            self.doors[door.name] = Door(self, door)

        self.model.find("**/garden").flatten_strong()
        self.model.find("**/transition_pieces").flatten_strong()
        self.locks_node.flatten_strong()
        self.floor_first_props = self.model.find("**/floor_first_props")
        self.floor_first_props.flatten_strong()
        self.floor_first_props.reparent_to(render)

        self.floor_second_props = self.model.find("**/floor_second_props")
        self.floor_second_props.flatten_strong()
        self.floor_second_props.reparent_to(render)

        #render.ls()
        #render.analyze()
        #PStatClient.connect()

        self.model.flatten_strong()
        #self.model.ls()
        #self.model.analyze()
