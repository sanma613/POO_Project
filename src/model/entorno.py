import pygame
import math
import time
import random
import sys

sys.path.append("src")

from utils.visual_effects import VisualEffects

class ObstaculoFuturista:
    """
    Representa un obstáculo futurista en el entorno del juego.
    Incluye diferentes tipos de obstáculos con efectos visuales únicos.
    """
    def __init__(self, x, y, ancho, alto):
        """
        Inicializa un nuevo ObstaculoFuturista.

        Args:
            x (int): Coordenada X de la esquina superior izquierda del obstáculo.
            y (int): Coordenada Y de la esquina superior izquierda del obstáculo.
            ancho (int): Ancho del obstáculo.
            alto (int): Alto del obstáculo.
        """
        self.x = x
        self.y = y
        self.ancho = ancho
        self.alto = alto
        # `rect` se utiliza para la detección de colisiones de forma eficiente.
        self.rect = pygame.Rect(x, y, ancho, alto)
        # `energy_pulse` controla la fase de animación para los efectos de energía.
        self.energy_pulse = random.uniform(0, 2 * math.pi)
        # Asigna un tipo de obstáculo aleatorio para variar la apariencia.
        self.obstacle_type = random.choice(["tech", "crystal", "barrier"])

    def update(self):
        """
        Actualiza el estado interno de los efectos visuales del obstáculo,
        como la fase del pulso de energía, para crear animaciones.
        """
        self.energy_pulse += 0.05 # Incrementa la fase para animar el pulso.

    def dibujar(self, superficie):
        """
        Dibuja el obstáculo en la superficie de Pygame con efectos visuales futuristas,
        basándose en su tipo (`obstacle_type`).

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará el obstáculo.
        """
        # Sombra: Dibuja una sombra ligera para dar profundidad.
        shadow_rect = pygame.Rect(self.rect.x + 4, self.rect.y + 4, self.rect.width, self.rect.height)
        pygame.draw.rect(superficie, (20, 20, 30), shadow_rect) # Color oscuro para la sombra.
        
        # Dibuja el obstáculo según su tipo.
        if self.obstacle_type == "tech":
            self._draw_tech_obstacle(superficie)
        elif self.obstacle_type == "crystal":
            self._draw_crystal_obstacle(superficie)
        else:
            self._draw_barrier_obstacle(superficie)
    
    def _draw_tech_obstacle(self, superficie):
        """
        Dibuja un obstáculo de tipo "tech" (tecnológico), con una base sólida,
        un borde y líneas de energía pulsantes.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará.
        """
        # Base del obstáculo.
        pygame.draw.rect(superficie, (60, 80, 120), self.rect) # Gris azulado.
        
        # Borde tecnológico usando `VisualEffects`.
        VisualEffects.draw_tech_border(superficie, self.rect, (100, 150, 200), 2)
        
        # Líneas de energía pulsantes:
        pulse_intensity = (math.sin(self.energy_pulse) + 1) / 2 # Intensidad varía con el pulso.
        energy_color = (int(100 + pulse_intensity * 100), int(150 + pulse_intensity * 50), 200) # Color pulsante.
        
        # Dibuja varias líneas horizontales a través del obstáculo.
        for i in range(3):
            y_pos = self.rect.y + (i + 1) * self.rect.height // 4
            pygame.draw.line(superficie, energy_color, 
                           (self.rect.x + 5, y_pos), 
                           (self.rect.x + self.rect.width - 5, y_pos), 2)
    
    def _draw_crystal_obstacle(self, superficie):
        """
        Dibuja un obstáculo de tipo "crystal" (cristalino), con forma hexagonal
        y un brillo interno pulsante.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará.
        """
        center = self.rect.center
        
        # Cristal principal (forma hexagonal):
        crystal_points = []
        for i in range(6):
            angle = i * math.pi / 3 # Ángulos para un hexágono.
            x = center[0] + (self.rect.width // 3) * math.cos(angle)
            y = center[1] + (self.rect.height // 3) * math.sin(angle)
            crystal_points.append((x, y))
        
        pygame.draw.polygon(superficie, (80, 120, 180), crystal_points) # Relleno azul-gris.
        pygame.draw.polygon(superficie, (120, 160, 220), crystal_points, 3) # Borde más claro.
        
        # Brillo interno pulsante:
        pulse_intensity = (math.sin(self.energy_pulse * 2) + 1) / 2 # Pulso más rápido.
        inner_color = (int(150 + pulse_intensity * 105), int(180 + pulse_intensity * 75), 255) # Color brillante.
        inner_size = int((self.rect.width // 6) * (0.5 + pulse_intensity * 0.5)) # Tamaño pulsante.
        pygame.draw.circle(superficie, inner_color, center, inner_size)
    
    def _draw_barrier_obstacle(self, superficie):
        """
        Dibuja un obstáculo de tipo "barrier" (barrera de energía), con una base
        sólida y un campo de fuerza translúcido pulsante.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará.
        """
        # Base sólida de la barrera.
        pygame.draw.rect(superficie, (40, 60, 80), self.rect) # Gris oscuro.
        
        # Campo de fuerza: Dibuja varias franjas translúcidas que pulsan en opacidad.
        for i in range(5):
            alpha = int(50 + 30 * (math.sin(self.energy_pulse + i * 0.5) + 1) / 2) # Opacidad pulsante con desfase.
            barrier_surface = pygame.Surface((self.rect.width, 4), pygame.SRCALPHA) # Superficie para la franja.
            barrier_color = (0, 150, 255, alpha) # Azul brillante con opacidad variable.
            pygame.draw.rect(barrier_surface, barrier_color, (0, 0, self.rect.width, 4))
            y_pos = self.rect.y + i * (self.rect.height // 5) # Posición de la franja.
            superficie.blit(barrier_surface, (self.rect.x, y_pos)) # Dibuja la franja en la superficie principal.

class PowerUpSalud:
    """
    Representa un power-up de salud que el jugador puede recoger.
    Tiene una duración limitada y un efecto visual de brillo.
    """
    def __init__(self, x, y, duracion=5):
        """
        Inicializa un nuevo PowerUpSalud.

        Args:
            x (int): Coordenada X del centro del power-up.
            y (int): Coordenada Y del centro del power-up.
            duracion (int, optional): Tiempo en segundos que el power-up permanecerá activo. Por defecto es 5.
        """
        self.x = x
        self.y = y
        self.radio = 10
        self.tiempo_creacion = time.time() # Registra el momento de su creación.
        self.duracion = duracion  # Segundos antes de que el power-up desaparezca.
        self.activo = True # Estado que indica si el power-up está activo.

    def rect(self):
        """
        Devuelve un objeto pygame.Rect que representa el área de colisión del power-up.

        Returns:
            pygame.Rect: El rectángulo de colisión del power-up.
        """
        return pygame.Rect(self.x - self.radio, self.y - self.radio, self.radio * 2, self.radio * 2)

    def actualizar(self):
        """
        Actualiza el estado del power-up, principalmente verificando si su duración ha expirado.
        Si la duración ha terminado, se desactiva.
        """
        if time.time() - self.tiempo_creacion > self.duracion:
            self.activo = False # Desactiva el power-up.

    def dibujar(self, superficie):
        """
        Dibuja el power-up de salud en la superficie de Pygame,
        incluyendo un círculo principal y un efecto de brillo.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará el power-up.
        """
        if not self.activo:
            return # No dibujar si el power-up no está activo.
        
        # Círculo principal del power-up (verde brillante).
        pygame.draw.circle(superficie, (0, 255, 100), (int(self.x), int(self.y)), self.radio)
        # Efecto de brillo alrededor del power-up utilizando `VisualEffects`.
        VisualEffects.draw_glow_circle(superficie, (0, 255, 100), (int(self.x), int(self.y)), self.radio, self.radio + 10)