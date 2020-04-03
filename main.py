import sys
import pman.shim

from direct.showbase.ShowBase import ShowBase
from direct.actor.Actor import Actor
from direct.gui.OnscreenText import OnscreenText

from panda3d.core import load_prc_file
from panda3d.core import Filename
from panda3d.core import BitMask32
from panda3d.core import CollisionTraverser
from panda3d.core import WindowProperties

from keybindings.device_listener import add_device_listener
from keybindings.device_listener import SinglePlayerAssigner

from character import Player, Monster
from map import Map
from direct.showbase import Audio3DManager

load_prc_file(
    Filename.expand_from('$MAIN_DIR/settings.prc')
)


class GameApp(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        pman.shim.init(self)

        info = self.pipe.getDisplayInformation()
        for idx in range(info.getTotalDisplayModes()):
            width = info.getDisplayModeWidth(idx)
            height = info.getDisplayModeHeight(idx)
            bits = info.getDisplayModeBitsPerPixel(idx)
        width = 1240
        height = 720
        print(width, height)
        wp = WindowProperties()
        #wp.set_undecorated(False)
        wp.set_size(width, height)
        base.win.requestProperties(wp)

        self.win.set_clear_color((0,0,0,0))
        self.accept('escape', sys.exit)
        add_device_listener(
            config_file='keybindings.toml',
            assigner=SinglePlayerAssigner(),
        )
        self.load_sound()
        self.font = loader.loadFont("font/Stanislav.otf")
        self.font.setPixelsPerUnit(120)
        self.start_game()
        #self.start_end()

    def start_game(self):
        self.mapmask = BitMask32(0x1)
        self.itemmask = BitMask32(0x2)
        self.map = Map("models/roem.bam")
        self.player = Player()
        self.load_sound()
        self.monsters = []
        self.monsters.append(Monster())

        self.text_a = OnscreenText(text="HENDRIK-JAN'S", fg=(0,0,0,1), scale=0.06, font=self.font)
        self.text_a.set_pos(-0.3,0,0.3)
        self.set_text_style(self.text_a)

        self.text_b = OnscreenText(text="SYNDACTYLY", fg=(0,0,0,1), scale=0.23, font=self.font)
        self.set_text_style(self.text_b)
        self.text_b.textNode.setShadow(0.02, 0.02)

        self.text_c = OnscreenText(text="listen closely (headphones essential)", fg=(1,1,1,1), scale=0.04, font=self.font)
        self.text_c.set_pos(0,0,0.-0.15)

        self.text_d = OnscreenText(text="hold left or right arrow to start", fg=(1,1,1,1), scale=0.04, font=self.font)
        self.text_d.set_pos(0,0,-0.1)
        self.text_shown = True

        self.taskMgr.add(self.update)

    def set_text_style(self, text):
        text.textNode.setSlant(0.5)
        text.textNode.setShadow(0.04, 0.04)
        text.textNode.setShadowColor(0.2, 0.2, 0.6, 1)
        text.set_scale(1,1,2)

    def start_end(self):
        self.scream = False
        for node in render.get_children():
            node.remove_node()
        base.cam.reparent_to(render)
        base.cam.set_pos(0,0,0)
        base.cam.set_hpr(0,0,0)
        base.camLens.set_fov(100)
        for sound in base.sounds3d:
            base.sounds3d[sound].stop()
        for sound in base.sounds2d:
            base.sounds2d[sound].stop()
        base.sounds2d["beat"].set_volume(0.4)
        base.sounds2d["beat"].play()
        self.end = Actor("models/end.bam")
        self.end.reparent_to(render)
        self.end.play("end")
        self.text = OnscreenText(text="WAKE UP", mayChange=True, fg=(1,1,1,1), scale=0.07, font=self.font)
        #self.set_text_style(self.text)
        self.taskMgr.add(self.ending)

    def load_sound(self):
        base.cTrav = CollisionTraverser() # only used for 3d audio
        self.sounds3d = {}
        self.sounds2d = {}

        try:
            self.audio3d = Audio3DManager.Audio3DManager(base.sfxManagerList[0], base.player.node)
            self.audio3d.setListenerVelocityAuto()
            sfx_files = [
                "roam_filter", "roam_normal", "scream_normal", "scream_filter", "loud_scream",
                "door_open", "door_closed"
            ]
            for sfx_file in sfx_files:
                sfx_path = "sfx/{}.wav".format(sfx_file)
                self.sounds3d[sfx_file] = self.audio3d.load_sfx(sfx_path)
                self.audio3d.setSoundVelocityAuto(self.sounds3d[sfx_file])
        except AttributeError:
            pass
        for sfx_file in ["key", "end", "walk", "scream_normal", "loud_scream", "beat"]:
            sfx_path = "sfx/{}.wav".format(sfx_file)
            self.sounds2d[sfx_file] = loader.load_sfx(sfx_path)
        self.sounds2d["walk"].set_loop(True)
        self.sounds2d["walk"].set_volume(0)
        self.sounds2d["walk"].play()
        self.sounds2d["beat"].set_loop(True)
        self.sounds2d["beat"].set_volume(0)
        self.sounds2d["beat"].play()
        self.beating=False

    def update(self, task):
        self.dt = globalClock.get_dt()
        self.player.control(self.device_listener.read_context('game'))
        for monster in self.monsters:
            monster.update()
        for door in self.map.doors:
            self.map.doors[door].update()
        if self.player.node.get_x() < -6.5:
            self.start_end()
            return
        return task.cont

    def ending(self, task):
        frame = self.end.get_current_frame()
        if frame%100 > 80:
            self.text.hide()
        elif frame%100 > 10:
            self.text.show()

        if frame > 600:
            sys.exit()
        elif frame > 570 and not self.scream:
            self.scream = True
            base.sounds2d["beat"].set_volume(0)
            self.sounds2d["scream_normal"].play()
            self.sounds2d["loud_scream"].play()
        elif frame > 500:
            self.text.text = "ARE YOU BEAUTIFUL?"
            if base.camLens.get_fov() > 70:
                base.camLens.set_fov(base.camLens.get_fov()-1)
        elif frame > 400:
            self.text.text = "AND SEE HOW WE DID?"
        elif frame > 300:
            self.text.text = "WHY DON'T YOU TAKE THIS MIRROR?"
        elif frame > 200:
            self.text.text = "THE OPERATION WAS A COMPLETE SUCCES"
        elif frame > 100:
            self.text.text = "YOU CAN OPEN YOUR EYES NOW"
        return task.cont

def main():
    app = GameApp()
    app.run()

if __name__ == '__main__':
    main()
