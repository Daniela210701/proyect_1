import pygame
import random
import math
import sys
import colorsys
import cv2
import numpy as np
import pyrealsense2 as rs
from ultralytics import YOLO  # Importamos la nueva red neuronal

# 1. CONFIGURACIÓN DE INTEL REALSENSE D455
pipeline = rs.pipeline()
config = rs.config()
config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
pipeline.start(config)

# 2. CONFIGURACIÓN DE YOLOv8 (Detector Multi-Persona)
# Cargamos el modelo nano (ligero y ultra rápido). Se descarga solo la primera vez.
model = YOLO("yolov8n.pt") 

# 3. INICIALIZACIÓN DE PYGAME
WIDTH, HEIGHT = 1400, 768
pygame.init()
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Instalación Interactiva BTL - Multi-Persona YOLOv8 + D455")
clock = pygame.time.Clock()

# Fuentes
font = pygame.font.SysFont("Arial", 16)
id_font = pygame.font.SysFont("Arial", 22, bold=True)

BLACK = (10, 10, 15)
PANEL_COLOR = (25, 25, 35)
INTERACTIVE_START_X = 420

# --- CLASES DEL MOTOR DE PARTÍCULAS ---
class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2.5, 2.5)
        self.vy = random.uniform(-2.5, 2.5)
        self.radius = random.uniform(4, 10)
        self.fade_speed = random.uniform(0.1, 0.2)
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
        self.size = random.uniform(15, 30)
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-3, 3)
        self.vx = random.uniform(-1, 1)
        self.vy = random.uniform(-3.5, -1)
        self.color = color
        self.life = 255
        self.fade_speed = random.uniform(3, 5)

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
            
            tri_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            color_with_alpha = self.color + (int(self.life),)
            pygame.draw.polygon(tri_surface, color_with_alpha, points, 2)
            surface.blit(tri_surface, (0, 0))

# --- GESTOR DE IDENTIDADES (COLORES ASIGNADOS POR ID) ---
class TrackedPerson:
    def __init__(self, person_id, x, y):
        self.id = person_id
        self.x = x
        self.y = y
        # Asignamos un color único fijo basado en el ID para que mantengan su identidad visual
        hue = (person_id * 0.13) % 1.0
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        self.color = (int(r * 255), int(g * 255), int(b * 255))

    def update_position(self, new_x, new_y):
        # Filtro de suavizado interactivo (60% anterior, 40% nuevo) para evitar vibraciones
        self.x = int(self.x * 0.6 + new_x * 0.4)
        self.y = int(self.y * 0.6 + new_y * 0.4)

# Diccionario para recordar a las personas activas y sus colores fijos
active_people = {}

particles = []
triangles = []

running = True
while running:
    screen.fill(BLACK)
    pygame.draw.rect(screen, PANEL_COLOR, (0, 0, INTERACTIVE_START_X, HEIGHT))
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # 1. CAPTURA DE LA REALSENSE
    frames = pipeline.wait_for_frames()
    color_frame = frames.get_color_frame()
    if not color_frame:
        continue

    color_image = np.asanyarray(color_frame.get_data())
    color_image = cv2.flip(color_image, 1)  # Efecto espejo intuitivo
    
    # 2. SEGUIMIENTO MULTI-PERSONA CON YOLO (Usamos el tracker nativo de YOLO)
    # classes=0 le indica que SOLO busque personas. persist=True mantiene los IDs entre frames.
    results = model.track(color_image, persist=True, classes=0, verbose=False)
    
    current_frame_ids = set()

    if results and results[0].boxes and results[0].boxes.id is not None:
        boxes = results[0].boxes.xyxy.cpu().numpy()  # Coordenadas de las cajas [x1, y1, x2, y2]
        ids = results[0].boxes.id.cpu().numpy().astype(int)  # IDs asignados por la IA
        
        for box, p_id in zip(boxes, ids):
            current_frame_ids.add(p_id)
            x1, y1, x2, y2 = box
            
            # Calculamos el centro exacto de la persona detectada en el espacio de la cámara
            cam_cx = int((x1 + x2) / 2)
            cam_cy = int((y1 + y2) / 2)
            
            # Dibujamos el cuadro de monitoreo e ID en el panel izquierdo (640x480 de la RealSense)
            cv2.rectangle(color_image, (int(x1), int(y1)), (int(x2), int(int(y2))), (0, 255, 200), 2)
            cv2.putText(color_image, f"ID: {p_id}", (int(x1), int(y1) - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 200), 2)
            
            # Mapeamos las coordenadas de la cámara al lienzo interactivo de la derecha
            norm_x = cam_cx / 640.0
            norm_y = cam_cy / 480.0
            interactive_x = INTERACTIVE_START_X + int(norm_x * (WIDTH - INTERACTIVE_START_X))
            interactive_y = int(norm_y * HEIGHT)
            
            # Si el ID es nuevo, lo registramos con su color único. Si ya existía, lo actualizamos.
            if p_id not in active_people:
                active_people[p_id] = TrackedPerson(p_id, interactive_x, interactive_y)
            else:
                active_people[p_id].update_position(interactive_x, interactive_y)

    # Limpiar del diccionario a las personas que ya se salieron de la escena
    for p_id in list(active_people.keys()):
        if p_id not in current_frame_ids:
            del active_people[p_id]

    # 3. DISPARAR PARTÍCULAS SEGÚN CADA PERSONA EN ESCENA
    for p_id, person in active_people.items():
        if random.random() < 0.55:
            particles.append(Particle(person.x, person.y, person.color))
        if random.random() < 0.12:
            triangles.append(Triangle3D(person.x, person.y, person.color))
            
        # Dibujar el indicador del usuario arriba de su centro en el lienzo negro
        id_txt = id_font.render(f"PLAYER_{person.id}", True, person.color)
        screen.blit(id_txt, (person.x - 45, person.y - 35))

    # 4. RENDERIZAR PANEL DE MONITOREO 2D (Izquierda)
    camera_surface = cv2.cvtColor(color_image, cv2.COLOR_BGR2RGB)
    camera_surface = np.rot90(camera_surface)
    camera_surface = pygame.surfarray.make_surface(camera_surface)
    camera_surface = pygame.transform.flip(camera_surface, True, False)
    camera_surface = pygame.transform.scale(camera_surface, (380, 285))
    screen.blit(camera_surface, (20, 80))

    # 5. ACTUALIZAR Y DIBUJAR GRÁFICOS INTERACTIVOS
    for p in particles[:]:
        p.update()
        if p.radius <= 0: particles.remove(p)
        else: p.draw(screen)

    for t in triangles[:]:
        t.update()
        if t.life <= 0: triangles.remove(t)
        else: t.draw(screen)

    # Interfaz / HUD Técnico
    title_txt = id_font.render("CONSOLA MULTI-DETECCIÓN YOLOv8", True, (255, 255, 255))
    screen.blit(title_txt, (20, 20))
    
    count_txt = font.render(f"PERSONAS DETECTADAS EN TIEMPO REAL: {len(active_people)}", True, (0, 255, 150))
    screen.blit(count_txt, (20, 390))
    
    inst_txt = font.render("Presiona Esc para salir", True, (120, 120, 120))
    screen.blit(inst_txt, (20, 720))

    pygame.display.flip()
    clock.tick(60)

pipeline.stop()
pygame.quit()
sys.exit()