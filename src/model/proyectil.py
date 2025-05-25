import pygame
import math
import sys

sys.path.append("src")

from utils.visual_effects import VisualEffects

class Proyectil:
    """
    Representa un proyectil disparado por un agente.
    Gestiona su movimiento, detección de colisiones con obstáculos,
    y efectos visuales como una estela y un brillo pulsante.
    """
    def __init__(self, x, y, target_x, target_y, velocidad=8):
        """
        Inicializa un nuevo Proyectil.

        Args:
            x (int): Coordenada X inicial del proyectil (generalmente la posición del agente que dispara).
            y (int): Coordenada Y inicial del proyectil.
            target_x (int): Coordenada X del punto objetivo hacia donde se dirige el proyectil.
            target_y (int): Coordenada Y del punto objetivo.
            velocidad (int, optional): Velocidad de movimiento del proyectil. Por defecto es 8.
        """
        self.x = x
        self.y = y
        self.velocidad = velocidad
        self.radio = 3 # Radio del círculo que representa el proyectil.
        self.activo = True # Indica si el proyectil está activo (no ha colisionado o salido de pantalla).
        
        # Calcular la dirección normalizada hacia el objetivo.
        dx = target_x - x
        dy = target_y - y
        distancia = math.hypot(dx, dy) # Calcula la distancia euclidiana.
        
        if distancia > 0:
            # Normaliza el vector de dirección y lo multiplica por la velocidad.
            self.vel_x = (dx / distancia) * velocidad
            self.vel_y = (dy / distancia) * velocidad
        else:
            # Si el objetivo es el mismo que el origen, el proyectil no se mueve.
            self.vel_x = 0
            self.vel_y = 0
        
        # --- Efectos visuales ---
        # `trail_positions` almacena las últimas posiciones para dibujar la estela.
        self.trail_positions = [(x, y)] * 3
        # `pulse_phase` controla la animación de pulso/brillo del proyectil.
        self.pulse_phase = 0
    
    def update(self, ancho_pantalla, alto_pantalla, obstaculos=[]):
        """
        Actualiza la posición del proyectil, sus efectos visuales y verifica colisiones.
        Desactiva el proyectil si colisiona con un obstáculo o sale de los límites de la pantalla.

        Args:
            ancho_pantalla (int): Ancho de la ventana de juego.
            alto_pantalla (int): Alto de la ventana de juego.
            obstaculos (list, optional): Lista de objetos de obstáculos con los que el proyectil puede colisionar. Por defecto es una lista vacía.
        """
        if not self.activo:
            return # Si el proyectil no está activo, no hay nada que actualizar.

        # Mover proyectil: Actualiza las coordenadas según su velocidad.
        self.x += self.vel_x
        self.y += self.vel_y

        # Verificar colisión con obstáculos:
        # Crea un rectángulo de colisión para el proyectil en su posición actual.
        proyectil_rect = pygame.Rect(int(self.x - self.radio), int(self.y - self.radio), self.radio * 2, self.radio * 2)
        for obstaculo in obstaculos:
            if proyectil_rect.colliderect(obstaculo.rect):
                self.activo = False # Desactiva el proyectil al colisionar.
                return  # Termina la actualización si choca.

        # Actualizar efectos visuales:
        self.pulse_phase += 0.3 # Incrementa la fase para la animación de pulso.
        self.trail_positions.pop() # Elimina la posición más antigua de la estela.
        self.trail_positions.insert(0, (self.x, self.y)) # Añade la posición actual al principio.

        # Desactivar si sale de pantalla:
        # Verifica si el proyectil ha abandonado los límites de la pantalla.
        if (self.x < 0 or self.x > ancho_pantalla or 
            self.y < 0 or self.y > alto_pantalla):
            self.activo = False
    
    def dibujar(self, superficie):
        """
        Dibuja el proyectil en la superficie de Pygame, incluyendo su estela
        y su efecto de brillo futurista.

        Args:
            superficie (pygame.Surface): La superficie donde se dibujará el proyectil.
        """
        if not self.activo:
            return # No dibujar si el proyectil no está activo.
        
        # Dibujar estela:
        # Itera sobre las posiciones almacenadas en `trail_positions` (excepto la actual)
        # para dibujar pequeños círculos que decrecen en opacidad y tamaño.
        for i, pos in enumerate(self.trail_positions[1:]):
            alpha = int(150 * (1 - i / len(self.trail_positions))) # Opacidad decreciente.
            trail_surface = pygame.Surface((6, 6), pygame.SRCALPHA) # Superficie temporal para la estela.
            trail_color = (0, 255, 255, alpha) # Color cian para la estela con opacidad.
            pygame.draw.circle(trail_surface, trail_color, (3, 3), max(1, 3 - i)) # Círculo de estela.
            superficie.blit(trail_surface, (int(pos[0] - 3), int(pos[1] - 3))) # Dibuja la estela.
        
        # Proyectil principal con brillo:
        center = (int(self.x), int(self.y))
        pulse_intensity = (math.sin(self.pulse_phase) + 1) / 2 # Intensidad del brillo pulsante.
        glow_radius = int(3 + pulse_intensity * 4) # Radio del brillo pulsante.
        
        # Dibuja un círculo de brillo utilizando la clase `VisualEffects`.
        VisualEffects.draw_glow_circle(superficie, (0, 255, 255), center, self.radio, glow_radius) # Cian brillante.
        # Dibuja un pequeño punto blanco en el centro para darle más intensidad.
        pygame.draw.circle(superficie, (255, 255, 255), center, 1)
    
    def colisiona_con(self, agente):
        """
        Verifica si el proyectil ha colisionado con un agente dado.
        Utiliza la distancia entre los centros y la suma de los radios para la detección.

        Args:
            agente (Agente): El objeto Agente con el que se desea verificar la colisión.

        Returns:
            bool: True si hay colisión, False en caso contrario.
        """
        if not self.activo:
            return False # Un proyectil inactivo no puede colisionar.
        
        # Calcula la distancia entre el centro del proyectil y el centro del agente.
        distancia = math.hypot(self.x - agente.x, self.y - agente.y)
        # Colisión ocurre si la distancia es menor que la suma de sus radios.
        return distancia < (self.radio + agente.radio)