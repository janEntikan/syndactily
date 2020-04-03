import sys
from math import sqrt
from random import uniform, choice
from direct.actor.Actor import Actor
from panda3d.core import Vec2, Vec3, Point3
from panda3d.core import NodePath
from panda3d.core import MainThread

from panda3d.core import CollideMask
from panda3d.core import CollisionHandlerQueue
from panda3d.core import CollisionHandlerPusher
from panda3d.core import CollisionNode
from panda3d.core import CollisionSegment
from panda3d.core import CollisionSphere
from panda3d.core import CollisionTraverser

from wezupath import PathFollower
from random import choice


class Character:
    def __init__(self, name, model):
        self.name = name
        self.node = NodePath(name + "_character")
        self.node.reparent_to(render)
        self.model = model
        self.model.reparent_to(self.node)
        self.traverser = CollisionTraverser()
        self.item_ray = self.ray("item", base.itemmask, point_b=(0,1,1))
        self.movement = Vec3(0,0,0)
        self.speed = 0.85
        self.keys = ""

    def ray(self, name, bitmask, point_a=(0,0,1), point_b=(0,0,0)):
        shape = CollisionSegment(point_a, point_b)
        col = CollisionNode(self.node.getName()+"-ray-"+name)
        col.add_solid(shape)
        col.set_from_collide_mask(bitmask)
        col.set_into_collide_mask(CollideMask.all_off())
        col_node = self.node.attach_new_node(col)
        handler = CollisionHandlerQueue()
        self.traverser.add_collider(col_node, handler)
        return {"collider":col,"shape":shape,"handler":handler,"node":col_node}

    def sphere(self, name, bitmask, pos=(0,0,1), radius=0.2):
        col = CollisionNode(self.node.getName()+"-sphere-"+name)
        shape = CollisionSphere(pos, radius)
        col.add_solid(shape)
        col.set_from_collide_mask(bitmask)
        col.set_into_collide_mask(CollideMask.allOff())
        col_node = self.node.attachNewNode(col)
        handler = CollisionHandlerPusher()
        handler.add_collider(col_node, self.node)
        self.traverser.add_collider(col_node, handler)
        return {"collider":col,"shape":shape,"handler":handler,"node":col_node}

    def fall(self):
        if self.fall_ray["handler"].get_num_entries() > 0:
            self.fall_ray["handler"].sort_entries()
            closest_entry = list(self.fall_ray["handler"].entries)[0]
            collision_position = closest_entry.get_surface_point(render)
            self.node.set_z(collision_position.get_z())
            self.movement.z = 0
        else:
            self.movement.z -= base.dt

    def open_doors(self):
        if self.item_ray["handler"].get_num_entries() > 0:
            closest_entry = list(self.item_ray["handler"].entries)[0]
            item = closest_entry.get_into_node_path()
            if item.name[0] == "d":
                door = base.map.doors[item.name]
                if not door.lock or door.lock in self.keys:
                    door.open = True


class Player(Character):
    def __init__(self):
        Character.__init__(self, "player", loader.load_model("models/person.bam"))
        self.fall_ray = self.ray("fall", base.mapmask)
        self.bump_sphere = self.sphere("bump", base.mapmask)
        base.cam.reparent_to(self.node)
        base.cam.set_pos(0,0,1.8)
        base.camLens.set_fov(100)
        base.camLens.set_near(0.1)
        self.node.set_pos(88.8,-14.45,0)
        #self.node.set_pos(10,0,0)
        self.node.set_h(-90)
        self.safe = True
        self.keys = ""
        self.beat_timer = 0

    def control(self, context):
        if context["movement"].y or context["movement"].x:
            if base.text_shown:
                base.text_a.remove_node()
                base.text_b.remove_node()
                base.text_c.remove_node()
                base.text_d.remove_node()
                base.text_shown = False

        self.node.set_h(self.node.get_h()-((context["movement"].x*90)*base.dt))
        self.movement.y += context["movement"].y*base.dt

        beatvol = base.sounds2d["beat"].get_volume()
        if context["movement"].y or base.monsters[0].distance < 10:
            if beatvol > 0:
                base.sounds2d["beat"].set_volume(beatvol-0.01)
            else:
                base.sounds2d["beat"].set_volume(0)
                self.beat_timer = 0
                base.beating = False
        else:
            self.beat_timer += base.dt
            if self.beat_timer > 4:
                if not base.beating:
                    base.beating = True
                    base.sounds2d["beat"].play()
                if beatvol < 0.4:
                    base.sounds2d["beat"].set_volume(beatvol+0.01)



        if context["movement"].y:
            base.sounds2d["walk"].set_volume(1)
        else:
            base.sounds2d["walk"].set_volume(0)
        self.node.set_pos(self.node, self.movement)
        self.traverser.traverse(base.map.collisions)
        self.fall()
        self.movement.x /= 2-self.speed
        self.movement.y /= 2-self.speed
        self.open_doors()

        pos = self.node.get_pos()
        if pos.z < 2 and pos.x > 68.13: # player is in safe zone.
            self.safe = True
        else:
            self.safe = False
        self.take_keys()

        if self.node.get_z(render) < 2 :
            base.map.floor_first_props.show()
            base.map.doors_node_f1.show()
            base.map.floor_second_props.hide()
            base.map.doors_node_f2.hide()
        else:
            base.map.floor_first_props.hide()
            base.map.doors_node_f1.hide()
            base.map.floor_second_props.show()
            base.map.doors_node_f2.show()

    def take_keys(self):
        if self.item_ray["handler"].get_num_entries() > 0:
            closest_entry = list(self.item_ray["handler"].entries)[0]
            item = closest_entry.get_into_node_path()
            if item.name[0] == "k":
                key = base.map.keys[item.name[-1:]]
                key.take(self)


class Monster(Character):
    def __init__(self):
        Character.__init__(self, "monster", Actor("models/skins.bam"))
        self.pathfinder = PathFollower(self.node)
        self.sect_ray = self.ray("sect", base.mapmask, point_a=(0,0,1),point_b=(0,1,1))
        self.model.loop("walk")
        self.nav_cooldown = 0
        self.chase_cooldown = 0
        self.state = self.roam
        self.roam_speed = 4
        self.chase_speed = 8
        self.keys = "roygbiv"
        self.jump_distance = 10
        self.sounds = [
            "roam_filter", "roam_normal",
            "scream_filter", "scream_normal",
            "loud_scream"
        ]
        for sound in self.sounds:
            base.audio3d.attachSoundToObject(base.sounds3d[sound], self.node)
            base.sounds3d[sound].set_loop(True)
            base.sounds3d[sound].play()
            base.sounds3d[sound].set_volume(0)
        self.active_sounds = ["roam"]
        self.filter = 0
        self.distance = 20

    def update(self):
        self.get_distance()
        self.state()
        self.open_doors()
        self.update_sound()
        v = choice((0.12, 0.08, 0.07))
        self.model.set_pos(uniform(-v,v),uniform(-v,v),uniform(-v,v))

    def get_distance(self):
        vec = self.node.get_pos(base.player.node)
        zdif = (abs(self.node.get_z()-base.player.node.get_z())/3)*10
        self.distance = sqrt(vec.x**2 + vec.y**2 + vec.z**2) +zdif
        if self.distance > 15: self.distance = 15
        if self.distance < 8:
            self.chase_speed = 20
        #elif self.distance < 4:
        #    self.chase_speed = 40
        else:
            self.chase_speed = 8
        if self.distance < 1.2:
            sys.exit() # PLAYER DIES

    def update_sound(self):
        for sound in self.sounds:
                base.sounds3d[sound].set_volume(0)
        for sound in self.active_sounds:
            try:
                base.sounds3d[sound+"_filter"].set_volume(self.filter)
                base.sounds3d[sound+"_normal"].set_volume(1-self.filter)
            except KeyError:
                base.sounds3d[sound].set_volume(1)

    def set_filter(self, walls):
        if walls < 0: walls = 0
        if walls > 10: walls = 10
        self.filter = walls/10
        zdif = abs(self.node.get_z() - base.player.node.get_z())/4 # extra filter for ceiling
        self.filter += zdif
        self.filter += 0.1 # corner jumpscare
        if self.filter > 1: self.filter = 1
        if self.filter < 0: self.filter = 0

    def goto(self, pos):
        try:
            self.pathfinder.follow_path(
                base.map.navigation_graph.find_path(self.node.get_pos(), pos)
            )
        except:
            pass

    def roam(self):
        self.pathfinder.move_speed = self.roam_speed
        self.pathfinder.turn_speed = self.roam_speed*100
        seen = self.scan_for_player()
        self.active_sounds = ["roam"]
        if seen and not base.player.safe:
            self.pathfinder.stop()
            self.state = self.chase
        elif not self.pathfinder.seq.is_playing():
            self.goto(choice(base.map.navigation_graph.graph["pos"]))
        self.pathfinder._update()

    def chase(self):
        if base.player.safe:
            self.last_seen = None
            self.state = self.roam
            return

        self.active_sounds = ["roam", "scream"]
        if self.distance < 6:
            self.active_sounds.append("loud_scream")
        self.pathfinder.move_speed = self.chase_speed
        self.pathfinder.turn_speed = self.chase_speed*100
        seen = self.scan_for_player()
        self.nav_cooldown -= base.dt
        self.chase_cooldown -= base.dt
        if seen:
            self.chase_cooldown = 5 # Higher values makes him "smarter"?
        if seen or self.chase_cooldown > 0:
            if self.nav_cooldown <= 0:
                self.goto(base.player.node.get_pos())
                self.nav_cooldown = 1 # How often to recalculate path to player
        elif not self.pathfinder.seq.is_playing():
            if self.last_seen:
                self.goto(self.last_seen)
            else:
                self.state = self.roam
                self.last_seen = None
        else:
            self.last_seen = None
        self.pathfinder._update()


    def scan_for_player(self):
        ppos = base.player.node.get_pos(self.node)
        ppos.z += 1
        self.sect_ray["shape"].set_point_b(ppos)
        self.traverser.traverse(base.map.collisions)
        if self.sect_ray["handler"].get_num_entries() == 0:
            self.filter = 0
            self.last_seen = base.player.node.get_pos(render)
            return self.last_seen
        else:
            self.set_filter(self.sect_ray["handler"].get_num_entries())
        return None
