import pygame
import math

class VisualEffects:
    """
    Clase de utilidad estática (no necesita ser instanciada) para dibujar
    varios efectos visuales futuristas y complejos en Pygame.
    Proporciona métodos para renderizar brillos, bordes tecnológicos, hexágonos
    y estelas de partículas, mejorando la estética del juego.
    """

    @staticmethod
    def draw_glow_circle(surface, color, center, radius, glow_radius=None):
        """
        Dibuja un círculo con un efecto de brillo (glow) suave a su alrededor.
        Este efecto se logra dibujando múltiples círculos concéntricos con opacidad decreciente.

        Args:
            surface (pygame.Surface): La superficie de Pygame donde se dibujará el brillo.
            color (tuple): El color RGB base del círculo y el brillo (ej. (0, 255, 255)).
                           El canal alfa (transparencia) se manejará internamente.
            center (tuple): Las coordenadas (x, y) del centro del círculo.
            radius (int): El radio del círculo principal opaco.
            glow_radius (int, optional): El radio máximo del efecto de brillo.
                                         Si es None, se calcula automáticamente (radius + 15).
        """
        if glow_radius is None:
            glow_radius = radius + 15 # Valor por defecto si no se especifica.
        
        # Crear una superficie temporal con formato SRCALPHA (soporte de transparencia).
        # Esta superficie será del tamaño suficiente para contener el brillo más grande.
        glow_surface = pygame.Surface((glow_radius * 2, glow_radius * 2), pygame.SRCALPHA)
        
        # Dibujar múltiples círculos con opacidad decreciente para crear el efecto de brillo.
        # Iteramos desde el radio exterior del brillo hacia el radio del círculo principal.
        for i in range(glow_radius, radius, -2): # Reduce el radio en pasos de 2 píxeles.
            # Calcular la opacidad: disminuye a medida que el círculo se hace más grande.
            # Se usa un factor (ej. 0.3) para que el brillo no sea completamente opaco.
            alpha = int(255 * (radius / i) * 0.3) 
            # Asegurarse de que los valores de color estén en el rango 0-255 y que el alfa sea válido.
            glow_color = (min(255, max(0, color[0])), 
                          min(255, max(0, color[1])), 
                          min(255, max(0, color[2])), 
                          max(0, min(255, alpha))) # Asegurar alpha entre 0 y 255
            
            # Dibuja el círculo translúcido en la superficie temporal, centrado en ella.
            pygame.draw.circle(glow_surface, glow_color, (glow_radius, glow_radius), i)
        
        # Dibuja el círculo principal, que es completamente opaco y con el color base,
        # también en la superficie temporal.
        pygame.draw.circle(glow_surface, color, (glow_radius, glow_radius), radius)
        
        # Blitear (pegar) la superficie temporal (con el brillo y el círculo principal)
        # en la superficie principal del juego, ajustando la posición para que el centro
        # coincida con el `center` original.
        surface.blit(glow_surface, (center[0] - glow_radius, center[1] - glow_radius))

    @staticmethod
    def draw_hexagon(surface, color, center, radius):
        """
        Dibuja un hexágono regular en la superficie.

        Args:
            surface (pygame.Surface): La superficie de Pygame donde se dibujará el hexágono.
            color (tuple): El color RGB del hexágono.
            center (tuple): Las coordenadas (x, y) del centro del hexágono.
            radius (int): El tamaño del hexágono (es el radio del círculo circunscrito,
                          es decir, la distancia del centro a cualquiera de sus vértices).
        Returns:
            list: Una lista de las coordenadas de los vértices del hexágono.
        """
        points = []
        for i in range(6):
            # Calcula los puntos de un hexágono regular.
            # El ángulo inicial se ajusta (-math.pi / 6 o -30 grados)
            # para que el hexágono tenga una arista horizontal en la parte superior.
            angle_rad = math.pi / 3 * i - math.pi / 6 
            x = center[0] + radius * math.cos(angle_rad)
            y = center[1] + radius * math.sin(angle_rad)
            points.append((int(x), int(y)))
        
        # Dibuja el polígono (hexágono) relleno. Si se quisiera solo el borde, se pasaría un grosor.
        pygame.draw.polygon(surface, color, points)
        return points # Devuelve los puntos, podría ser útil para depuración o futuras interacciones.
    
    @staticmethod
    def draw_tech_border(surface, rect, color, thickness=2):
        """
        Dibuja un borde futurista o "tecnológico" alrededor de un rectángulo.
        Este efecto se logra dibujando un polígono con esquinas "cortadas" o anguladas,
        dando una apariencia más moderna y de circuito.

        Args:
            surface (pygame.Surface): La superficie de Pygame donde se dibujará el borde.
            rect (pygame.Rect): El objeto Rect de Pygame que define la posición y tamaño
                                del área alrededor de la cual se dibujará el borde.
            color (tuple): El color RGB del borde.
            thickness (int, optional): El grosor del borde. Por defecto es 2.
        """
        x, y, w, h = rect.x, rect.y, rect.width, rect.height
        corner_size = 8 # Define el tamaño del "corte" en las esquinas para el efecto tecnológico.
        
        # Define los puntos que forman el polígono del borde con las esquinas cortadas.
        # En lugar de las 4 esquinas clásicas, hay 8 puntos.
        points = [
            (x + corner_size, y), (x + w - corner_size, y),  # Lado superior (con cortes)
            (x + w, y + corner_size), (x + w, y + h - corner_size),  # Lado derecho (con cortes)
            (x + w - corner_size, y + h), (x + corner_size, y + h),  # Lado inferior (con cortes)
            (x, y + h - corner_size), (x, y + corner_size)  # Lado izquierdo (con cortes)
        ]
        # Dibuja el polígono del borde.
        pygame.draw.polygon(surface, color, points, thickness)
    
    @staticmethod
    def draw_particle_trail(surface, start_pos, end_pos, color, particles=8):
        """
        Dibuja una estela (trail) de partículas translúcidas entre dos puntos.
        Crea un efecto de rastro o movimiento.

        Args:
            surface (pygame.Surface): La superficie de Pygame donde se dibujarán las partículas.
            start_pos (tuple): Las coordenadas (x, y) del punto de inicio de la estela.
            end_pos (tuple): Las coordenadas (x, y) del punto final de la estela.
            color (tuple): El color RGB base de las partículas.
            particles (int, optional): El número de partículas en la estela. Cuantas más, más denso el rastro.
                                       Por defecto es 8.
        """
        for i in range(particles):
            # Calcula una posición interpolada linealmente entre start_pos y end_pos.
            # 't' varía de 0 a 1, moviéndose a lo largo de la línea.
            t = i / particles
            x = start_pos[0] + (end_pos[0] - start_pos[0]) * t
            y = start_pos[1] + (end_pos[1] - start_pos[1]) * t
            
            # Calcula la opacidad de la partícula, disminuyendo a medida que se aleja del end_pos.
            # Esto crea un efecto de desvanecimiento en la cola.
            alpha = int(255 * (1 - t) * 0.7) # Factor 0.7 para que no sea completamente opaco.
            
            # Crea una superficie temporal para cada partícula para aplicar transparencia individual.
            particle_surface = pygame.Surface((4, 4), pygame.SRCALPHA) # Pequeña superficie de 4x4 píxeles.
            particle_color = (*color[:3], alpha) # Combina el color RGB con el alfa calculado.
            
            # Dibuja un círculo pequeño (la partícula) en el centro de su superficie temporal.
            pygame.draw.circle(particle_surface, particle_color, (2, 2), 2)
            
            # Blitea la partícula en la superficie principal, ajustando la posición para que
            # el centro del círculo coincida con la posición (x, y) calculada.
            surface.blit(particle_surface, (int(x - 2), int(y - 2)))