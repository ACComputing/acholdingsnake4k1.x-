#!/usr/bin/env python3
"""
[C] Atrari [C] A.C Holdings snake 60 fps py port
TEAM HUMMER | FAMICOM EDITION
Authentic discrete frame movement, locked 60 FPS, chiptune SFX.
Single-file. Drop-in run. Python 3.9+ | pygame 2.x
"""
import pygame, sys, random, array, struct

# ====================== CONSTANTS ======================
SW, SH = 640, 480
COLS, ROWS = 20, 15
BLK = 28
GRID_X = (SW - COLS * BLK) // 2
GRID_Y = (SH - ROWS * BLK) // 2
FPS = 60

C_BG = (12, 12, 24)
C_GRID = (28, 28, 48)
C_WHITE = (255, 255, 255)
C_DGRAY = (80, 80, 100)
C_GREEN = (52, 188, 52)
C_DGREEN = (24, 112, 24)
C_RED = (220, 40, 40)
C_YELLOW = (255, 212, 0)
C_BLUE = (60, 120, 248)
C_PBG = (16, 16, 32)
C_PBOR = (60, 60, 90)

# ====================== AUDIO ENGINE (GB/NES Style) ======================
SR = 44100

def _pulse(freq, dur, duty=0.25, vol=0.25, decay=0.0, cut=0.9):
    n = int(SR * dur); cs = int(n * cut)
    out = array.array('h')
    for i in range(n):
        if freq <= 0 or i >= cs: out.append(0); continue
        t = i / SR
        w = 1.0 if (freq * t) % 1.0 < duty else -1.0
        v = max(0.0, vol - decay * t) if decay > 0 else vol
        out.append(int(max(-32767, min(32767, w * v * 32767))))
    return out

def _noise(dur, vol=0.12, pitch=5):
    n = int(SR * dur); out = array.array('h'); lfsr = 0x7FFF; ctr = 0
    per = max(1, pitch * 4); cb = 1
    for i in range(n):
        ctr += 1
        if ctr >= per:
            ctr = 0; b0 = lfsr & 1; b1 = (lfsr >> 1) & 1
            lfsr = (lfsr >> 1) | ((b0 ^ b1) << 14); cb = 1 if lfsr & 1 else -1
        v = vol * max(0.0, 1.0 - (i / n) * 1.2)
        out.append(int(max(-32767, min(32767, cb * v * 32767))))
    return out

def _snd(raw): return pygame.mixer.Sound(buffer=struct.pack(f'<{len(raw)}h', *raw))
def _mix(*arrs):
    ml = max(len(a) for a in arrs); m = array.array('h', [0] * ml)
    for a in arrs:
        for i in range(len(a)): m[i] = int(max(-32767, min(32767, m[i] + a[i])))
    return m

SFX = {}
def _init_audio():
    SFX['menu']   = _snd(_pulse(880, 0.03, 0.125, 0.1, cut=0.85))
    SFX['select'] = _snd(_mix(_pulse(880, 0.03, 0.25, 0.12), _pulse(1320, 0.05, 0.25, 0.1)))
    SFX['move']   = _snd(_pulse(600, 0.02, 0.25, 0.08, cut=0.9))
    SFX['eat']    = _snd(_mix(_pulse(523, 0.06, 0.5, 0.2), _pulse(784, 0.06, 0.5, 0.18)))
    SFX['crash']  = _snd(_mix(_noise(0.15, 0.2, 3), _pulse(120, 0.1, 0.5, 0.15)))
    SFX['over']   = _snd(_mix(_pulse(392,0.2,0.5,0.2,decay=1.0), _pulse(330,0.2,0.5,0.18,decay=1.0), _pulse(262,0.4,0.5,0.2,decay=0.8)))

# ====================== FAMICOM TIMING MODEL ======================
class FamiTimer:
    def __init__(self, start_delay=10, min_delay=3):
        self.delay, self.min_delay, self.counter, self.score = start_delay, min_delay, 0, 0
    def tick(self):
        self.counter += 1
        if self.counter >= self.delay: self.counter = 0; return True
        return False
    def update_speed(self, new_score):
        self.score = new_score; self.delay = max(self.min_delay, 10 - int(self.score / 5))

# ====================== SNAKE ENGINE ======================
class SnakeGame:
    def __init__(self):
        self.body = [(10,7),(9,7),(8,7)]; self.dir = self.next_dir = (1,0)
        self.food = self._spawn_food(); self.score = self.high = 0; self.alive = True
        self.timer = FamiTimer()
    def _spawn_food(self):
        while True:
            fx, fy = random.randint(0,COLS-1), random.randint(0,ROWS-1)
            if (fx,fy) not in self.body: return (fx,fy)
    def handle_input(self, key):
        if not self.alive: return
        if key == pygame.K_LEFT and self.dir != (1,0): self.next_dir = (-1,0)
        elif key == pygame.K_RIGHT and self.dir != (-1,0): self.next_dir = (1,0)
        elif key == pygame.K_UP and self.dir != (0,1): self.next_dir = (0,-1)
        elif key == pygame.K_DOWN and self.dir != (0,-1): self.next_dir = (0,1)
    def frame_step(self):
        if not self.timer.tick() or not self.alive: return False
        self.dir = self.next_dir
        nh = (self.body[0][0]+self.dir[0], self.body[0][1]+self.dir[1])
        if nh[0]<0 or nh[0]>=COLS or nh[1]<0 or nh[1]>=ROWS or nh in self.body:
            self.alive = False
            if self.score > self.high: self.high = self.score
            return 'crash'
        self.body.insert(0, nh)
        if nh == self.food:
            self.score += 1; self.timer.update_speed(self.score); self.food = self._spawn_food(); return 'eat'
        else: self.body.pop(); return 'move'

# ====================== RENDERING ======================
def _font(sz, bold=True): return pygame.font.SysFont('couriernew', sz, bold=bold)
def dblk(srf,x,y,c,sz=BLK):
    bw = max(2,sz//8)
    pygame.draw.rect(srf,c,(x,y,sz,sz)); pygame.draw.rect(srf,C_WHITE,(x,y,sz,bw))
    pygame.draw.rect(srf,C_WHITE,(x,y,bw,sz)); pygame.draw.rect(srf,(0,0,0),(x,y+sz-bw,sz,bw))
    pygame.draw.rect(srf,(0,0,0),(x+sz-bw,y,bw,sz))
def dtc(srf,txt,f,c,y,cx=SW//2): r=f.render(txt,True,c); srf.blit(r,(cx-r.get_width()//2,y))
def dpnl(srf,x,y,w,h,title=""):
    pygame.draw.rect(srf,C_PBG,(x,y,w,h)); pygame.draw.rect(srf,C_PBOR,(x,y,w,h),2)
    if title: dtc(srf,title,_font(10),C_YELLOW,y+4,x+w//2)

# ====================== MAIN APP ======================
class App:
    def __init__(self):
        pygame.init(); pygame.mixer.init(frequency=SR,size=-16,channels=1,buffer=2048); _init_audio()
        self.scr = pygame.display.set_mode((SW,SH))
        pygame.display.set_caption("[C] Atrari [C] A.C Holdings snake 60 fps py port")
        self.clk = pygame.time.Clock()
        # Adjusted font sizes: main title now uses a smaller font (18) to fit the screen
        self.ft_title = _font(18)          # was 28 – now shrunk
        self.ft = _font(28)                # kept for short titles (HOW TO PLAY, GAME OVER)
        self.fm = _font(16)
        self.fs = _font(12)
        self.fst = _font(10)
        self.state,self.mi,self.g = 'menu',0,SnakeGame()
        self.scan = pygame.Surface((SW,SH),pygame.SRCALPHA)
        for y in range(0,SH,4): pygame.draw.line(self.scan,(0,0,0,12),(0,y+2),(SW,y+2))
    def _psfx(self,name): 
        if name in SFX: SFX[name].play()
    def _draw_menu(self,title,lines):
        dtc(self.scr,title,self.ft,C_RED,60); y=130
        for l in lines: dtc(self.scr,l,self.fst,C_YELLOW if l.isupper() and len(l)<30 else C_DGRAY,y); y+=24
        dtc(self.scr,"PRESS ESC OR ENTER TO RETURN",self.fs,C_DGRAY,SH-40)
    def _draw_game(self):
        pygame.draw.rect(self.scr,(8,8,18),(GRID_X-2,GRID_Y-2,COLS*BLK+4,ROWS*BLK+4))
        pygame.draw.rect(self.scr,C_PBOR,(GRID_X-3,GRID_Y-3,COLS*BLK+6,ROWS*BLK+6),2)
        for r in range(ROWS):
            for c in range(COLS): pygame.draw.rect(self.scr,C_GRID,(GRID_X+c*BLK,GRID_Y+r*BLK,BLK,BLK),1)
        for i,(sx,sy) in enumerate(self.g.body):
            dblk(self.scr,GRID_X+sx*BLK,GRID_Y+sy*BLK, C_GREEN if i==0 else (C_DGREEN if i<3 else C_BLUE))
        dblk(self.scr,GRID_X+self.g.food[0]*BLK,GRID_Y+self.g.food[1]*BLK,C_RED)
        rx = GRID_X+COLS*BLK+15
        dpnl(self.scr,rx,GRID_Y,140,60,"SCORE"); dtc(self.scr,f"{self.g.score:04d}",self.fm,C_WHITE,GRID_Y+20,rx+70)
        dpnl(self.scr,rx,GRID_Y+75,140,55,"SPEED"); dtc(self.scr,f"L{10-self.g.timer.delay+1}",self.fm,C_YELLOW,GRID_Y+95,rx+70)
        dpnl(self.scr,rx,GRID_Y+145,140,55,"HIGH"); dtc(self.scr,f"{self.g.high:04d}",self.fm,C_DGRAY,GRID_Y+165,rx+70)
        if not self.g.alive:
            ov=pygame.Surface((SW,SH),pygame.SRCALPHA); ov.fill((0,0,0,180)); self.scr.blit(ov,(0,0))
            dtc(self.scr,"GAME OVER",self.ft,C_RED,SH//2-60); dtc(self.scr,f"SCORE: {self.g.score}",self.fm,C_WHITE,SH//2-10)
            dtc(self.scr,"ENTER: RETRY   ESC: MENU",self.fs,C_DGRAY,SH//2+30)
    def _draw_main_menu(self):
        # Title – now uses smaller font and adjusted Y position for perfect centering
        dtc(self.scr,"[ac holdings snake 60 fps m4 pro py port]",self.ft_title,C_GREEN,70)
        dtc(self.scr,"TEAM HUMMER | FAMICOM EDITION",self.fs,C_YELLOW,105)
        items=['START GAME','HOW TO PLAY','CREDITS','ABOUT GAME']; y=180   # moved down for better balance
        for i,l in enumerate(items):
            sel=i==self.mi; c=C_WHITE if sel else C_DGRAY; dtc(self.scr,l,self.fm,c,y)
            if sel and pygame.time.get_ticks()%500<300:
                a=_font(14).render(">",True,C_RED); self.scr.blit(a,(SW//2-a.get_width()//2-40,y))
            y+=36
        dtc(self.scr,"PRESS ENTER TO SELECT",self.fst,C_DGRAY,SH-40)
    def _evt(self,e):
        if e.type!=pygame.KEYDOWN: return
        k=e.key
        if self.state=='menu':
            if k==pygame.K_UP: self.mi=(self.mi-1)%4; self._psfx('menu')
            elif k==pygame.K_DOWN: self.mi=(self.mi+1)%4; self._psfx('menu')
            elif k in (pygame.K_RETURN,pygame.K_SPACE):
                self._psfx('select')
                if self.mi==0: self.g=SnakeGame(); self.state='play'
                else: self.state=['menu','howto','credits','about'][self.mi]
        elif self.state in('howto','credits','about') and k in(pygame.K_ESCAPE,pygame.K_RETURN): self.state='menu';self._psfx('menu')
        elif self.state=='play':
            if self.g.alive:
                self.g.handle_input(k)
                if k in(pygame.K_p,pygame.K_ESCAPE): self.state='paused'
            else:
                if k==pygame.K_RETURN: self.g=SnakeGame();self._psfx('select')
                elif k==pygame.K_ESCAPE: self.state='menu';self._psfx('menu')
        elif self.state=='paused' and k in(pygame.K_p,pygame.K_ESCAPE): self.state='play'
    def _upd(self):
        if self.state=='play' and self.g.alive:
            ev=self.g.frame_step()
            if ev: self._psfx(ev)
    def _drw(self):
        self.scr.fill(C_BG)
        if self.state=='menu': self._draw_main_menu()
        elif self.state=='howto': self._draw_menu("HOW TO PLAY",["ARROWS: CHANGE DIRECTION","EAT RED BLOCKS TO GROW","DON'T HIT WALLS OR YOURSELF","","SPEED INCREASES EVERY 5 APPLES","FAMICOM-STYLE FRAME MOVEMENT","","60 FPS RENDER LOCK"])
        elif self.state=='credits': self._draw_menu("CREDITS",["GAME DESIGN & CODE","TEAM HUMMER","","AUDIO ENGINE","GB/NES PULSE + NOISE SYNTH","","INSPIRATION","CLASSIC 1980s ARCADE SNAKE","","THANKS FOR PLAYING!"])
        elif self.state=='about': self._draw_menu("ABOUT GAME",["HUMMER SNAKE v1.0","FAMICOM TIMING MODEL","DISCRETE FRAME STEPPING","NO DT, NO INTERPOLATION","","AUTHENTIC 8-BIT SPEED CURVE","INSTANT LOCK, PURE INPUT","PYTHON 3.x + PYGAME"])
        elif self.state in('play','paused'):
            self._draw_game()
            if self.state=='paused':
                ov=pygame.Surface((SW,SH),pygame.SRCALPHA); ov.fill((0,0,0,160)); self.scr.blit(ov,(0,0))
                dtc(self.scr,"PAUSED",self.ft,C_YELLOW,SH//2-30); dtc(self.scr,"PRESS P OR ESC",self.fs,C_DGRAY,SH//2+20)
        self.scr.blit(self.scan,(0,0)); pygame.display.flip()
    def run(self):
        while True:
            for e in pygame.event.get():
                if e.type==pygame.QUIT: pygame.quit();sys.exit()
                self._evt(e)
            self._upd();self._drw();self.clk.tick(FPS)

if __name__=='__main__':
    import os,sys
    if sys.platform=='darwin': os.environ.setdefault('SDL_VIDEO_DRIVER','cocoa')
    App().run()
