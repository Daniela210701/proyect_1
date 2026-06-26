import pygame
import random
import math
import sys
import colorsys
import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO
import os

# 1. CONFIGURACIÓN DE INTEL REALSENSE D455
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

# 2. CONFIGURACIÓN DE YOLOv8
model = YOLO("yolov8n.pt") 

# 3. CONFIGURACIÓN DE VENTANAS (DUAL MONITOR)
pygame.init()

# Dimensiones de las pantallas
MONITOR_1_WIDTH, MONITOR_1_HEIGHT = 800, 600   # Consola técnica (Laptop)
MONITOR_2_WIDTH, MONITOR_2_HEIGHT = 1920, 1080 # Arte interactivo (Proyector/Pantalla 2)

# --- VENTANA 1: CONSOLA DE MONITOREO (Pantalla Principal) ---
# Centrada por defecto en tu monitor principal
screen_control = pygame.display.set_mode((MONITOR_1_WIDTH, MONITOR_1_HEIGHT))
pygame.display.set_caption("CONSOLA DE CONTROL Y VISIÓN - REALSENSE")

# --- VENTANA 2: LIENZO INTERACTIVO (Segunda Pantalla) ---
# Truco de entorno: Posicionamos la segunda ventana justo donde termina el primer monitor (X = MONITOR_1_WIDTH)
os.environ['SDL_VIDEO_WINDOW_POS'] = f"{MONITOR_1_WIDTH},0"

# Creamos la ventana de arte. Si quieres que se haga pantalla completa real en el proyector, 
# puedes agregar el flag: pygame.FULLSCREEN
screen_art = pygame.display.set_mode((MONITOR_2_WIDTH, MONITOR_2_HEIGHT))
# Le quitamos los bordes de ventana de Windows para que se vea limpio como instalación
# screen_art = pygame.display.set_mode((MONITOR_2_WIDTH, MONITOR_2_HEIGHT), pygame.NOFRAME)

clock = pygame.time.Clock()

# Fuentes
font = pygame.font.SysFont("Arial", 18)
id_font = pygame.font.SysFont("Arial", 28, bold=True)

BLACK = (10, 10, 15)

# --- CLASES DEL MOTOR DE PARTÍCULAS ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-3, 3)
        self.vy = random.uniform(-3, 3)
        self.radius = random.uniform(5, 14)
        self.fade_speed = random.uniform(0.12, 0.25)
        self.color = color

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.radius -= self.fade_speed

    def draw(self, surface):
        if self.radius > 0:
            pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), int(self.radius))

class Triangle3D:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.size = random.uniform(20, 45)
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-4, 4)
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-4, -1.5)
        self.color = color
        self.life = 255
        self.fade_speed = random.uniform(3.5, 5.5)

    def update(self):
        self.x += self.vx
        self.y += self.vy
        self.angle += self.rot_speed
        self.life -= self.fade_speed

    def draw(self, surface):
        if self.life > 0:
            points = []
            for i in range(3):
                a = math.radians(self.angle + i * 120)
                px = self.x + self.size * math.cos(a)
                py = self.y + self.size * math.sin(a)
                points.append((px, py))
            
            tri_surface = pygame.Surface((MONITOR_2_WIDTH, MONITOR_2_HEIGHT), pygame.SRCALPHA)
            color_with_alpha = self.color + (int(self.life),)
            pygame.draw.polygon(tri_surface, color_with_alpha, points, 2)
            surface.blit(tri_surface, (0, 0))

class TrackedPerson:
    def __init__(self, person_id, x, y):
        self.id = person_id
        self.x = x
        self.y = y
        hue = (person_id * 0.13) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        self.color = (int(r * 255), int(g * 255), int(b * 255))

    def update_position(self, new_x, new_y):
        self.x = int(self.x * 0.55 + new_x * 0.45)
        self.y = int(self.y * 0.55 + new_y * 0.45)

active_people = {}
particles = []
triangles = []

running = True
while running:
    # Limpiamos ambos lienzos independientes
    screen_control.fill((20, 20, 30)) # Fondo gris técnico para control
    screen_art.fill(BLACK)             # Fondo negro puro para la proyección
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # 1. CAPTURA D455
    frames = pipeline.wait_for_frames()
    color_frame = frames.get_color_frame()
    if not color_frame:
        continue

    color_image = np.asanyarray(color_frame.get_data())
    color_image = cv2.flip(color_image, 1) # Espejo
    
    # 2. SEGUIMIENTO DE LA IA (YOLOv8)
    results = model.track(color_image, persist=True, classes=0, verbose=False)
    current_frame_ids = set()

    if results and results[0].boxes and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()
        ids = results[0].boxes.id.cpu().numpy().astype(int)
        
        for box, p_id in zip(boxes, ids):
            current_frame_ids.add(p_id)
            x1, y1, x2, y2 = box
            
            cam_cx = int((x1 + x2) / 2)
            cam_cy = int((y1 + y2) / 2)
            
            # Pintamos los vectores y recuadros de análisis técnico sobre la imagen OpenCV
            cv2.rectangle(color_image, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 180), 2)
            cv2.circle(color_image, (cam_cx, cam_cy), 5, (255, 0, 0), -1)
            cv2.putText(color_image, f"TRACKING ID: {p_id}", (int(x1), int(y1) - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 180), 2)
            
            # MAPEO EXCLUSIVO: Escalamos las coordenadas de la cámara al tamaño de la SEGUNDA pantalla (1920x1080)
            norm_x = cam_cx / 640.0
            norm_y = cam_cy / 480.0
            art_x = int(norm_x * MONITOR_2_WIDTH)
            art_y = int(norm_y * MONITOR_2_HEIGHT)
            
            if p_id not in active_people:
                active_people[p_id] = TrackedPerson(p_id, art_x, art_y)
            else:
                active_people[p_id].update_position(art_x, art_y)

    # Limpieza de bajas
    for p_id in list(active_people.keys()):
        if p_id not in current_frame_ids:
            del active_people[p_id]

    # 3. CONSTRUCCIÓN DEL RENDER GRÁFICO DE PARTÍCULAS (Hacia la ventana de Arte)
    for p_id, person in active_people.items():
        if random.random() < 0.6:
            particles.append(Particle(person.x, person.y, person.color))
        if random.random() < 0.15:
            triangles.append(Triangle3D(person.x, person.y, person.color))
            
        # Dibujamos las etiquetas estéticas de los jugadores en la pantalla de Arte
        id_txt = id_font.render(f"PLAYER_{person.id}", True, person.color)
        screen_art.blit(id_txt, (person.x - 55, person.y - 45))

    # Actualizar posiciones y renderizar en la pantalla interactiva (Lienzo de arte)
    for p in particles[:]:
        p.update()
        if p.radius <= 0: particles.remove(p)
        else: p.draw(screen_art)

    for t in triangles[:]:
        t.update()
        if t.life <= 0: triangles.remove(t)
        else: t.draw(screen_art)

    # 4. RENDERIZAR LA SEÑAL DE DETECCIÓN (Hacia la ventana de Control)
    camera_surface = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
    camera_surface = np.rot90(camera_surface)
    camera_surface = pygame.surfarray.make_surface(camera_surface)
    camera_surface = pygame.transform.flip(camera_surface, True, False)
    # Escalamos el video para que ocupe gran parte de la consola de la laptop
    camera_surface = pygame.transform.scale(camera_surface, (760, 480))
    screen_control.blit(camera_surface, (20, 20))

    # Información del sistema en la pantalla de control de la laptop
    info_txt = font.render(f"Estado del Sistema: OPERATIVO | Usuarios Interactuando: {len(active_people)}", True, (255, 255, 255))
    screen_control.blit(info_txt, (20, 520))
    fps_txt = font.render(f"Rendimiento de Render: {int(clock.get_fps())} FPS", True, (0, 255, 120))
    screen_control.blit(fps_txt, (20, 550))

    # ACTUALIZAR AMBAS PANTALLAS EN PARALELO
    pygame.display.update()
    clock.tick(60)

pipeline.stop()
pygame.quit()
sys.exit()