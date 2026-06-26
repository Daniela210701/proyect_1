import pygame
import random
import math
import sys
import colorsys # Nos ayudará a hacer el cambio de color suave

# Inicialización de Pygame
pygame.init()
WIDTH, HEIGHT = 1024, 768
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("D455 Interactivo - Evolución de Color")
clock = pygame.time.Clock()

BLACK = (10, 10, 15)

# Variable global para controlar el tono (cambia con el tiempo)
# En HSV, el tono (Hue) va de 0.0 a 1.0
current_hue = 0.0

def get_dynamic_color(hue_offset=0.0):
    """Genera un color RGB basado en el tono actual + un desfase"""
    # Sumamos el desfase y usamos el operador módulo (%) para mantenerlo entre 0.0 y 1.0
    hue = (current_hue + hue_offset) % 1.0
    # Convertimos HSV (Tono, Saturación al 100%, Brillo al 100%) a RGB (valores 0-1)
    r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
    # Retornamos en formato 0-255 que usa Pygame
    return (int(r * 255), int(g * 255), int(b * 255))

class Particle:
    def __init__(self, x, y, color):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2.5, 2.5)
        self.vy = random.uniform(-2.5, 2.5)
        self.radius = random.uniform(3, 10)
        self.fade_speed = random.uniform(0.08, 0.2)
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
        self.size = random.uniform(12, 30)
        self.angle = random.uniform(0, 360)
        self.rot_speed = random.uniform(-3, 3)
        self.vx = random.uniform(-1.5, 1.5)
        self.vy = random.uniform(-3.5, -1)
        self.color = color
        self.life = 255
        self.fade_speed = random.uniform(2.5, 4.5)

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

particles = []
triangles = []

running = True
while running:
    screen.fill(BLACK)
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False

    # Avanzamos el tono global paulatinamente para cambiar los colores de las NUEVAS partículas
    current_hue += 0.002 # Controla la velocidad del cambio de color arcoíris
    if current_hue > 1.0:
        current_hue = 0.0

    # SIMULACIÓN: Obtenemos la posición del mouse
    mouse_pos = pygame.mouse.get_pos()
    active_targets = [mouse_pos] # Aquí caerán las N personas de la cámara
    
    for target in active_targets:
        tx, ty = target
        
        # Generamos partículas con el color del ciclo actual
        if random.random() < 0.5:
            # Mandamos el color base
            p_color = get_dynamic_color()
            particles.append(Particle(tx, ty, p_color))
            
        if random.random() < 0.12:
            # A los triángulos les damos un ligero desfase (0.1) para que contrasten
            t_color = get_dynamic_color(hue_offset=0.1)
            triangles.append(Triangle3D(tx, ty, t_color))

    # Actualizar y dibujar partículas existentes (estas mantienen el color con el que nacieron)
    for p in particles[:]:
        p.update()
        if p.radius <= 0:
            particles.remove(p)
        else:
            p.draw(screen)

    # Actualizar y dibujar triángulos existentes
    for t in triangles[:]:
        t.update()
        if t.life <= 0:
            triangles.remove(t)
        else:
            t.draw(screen)

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()