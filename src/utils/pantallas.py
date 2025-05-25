import pygame
import sys

def pantalla_bienvenida(pantalla, ancho, alto):
    """
    Muestra una pantalla de bienvenida con un título y un botón interactivo
    para comenzar el juego. Espera a que el usuario haga clic sobre el botón
    o cierre la ventana.

    Args:
        pantalla (pygame.Surface): Superficie donde se dibujan los elementos.
        ancho (int): Ancho de la pantalla.
        alto (int): Alto de la pantalla.
    """
    pygame.font.init()
    clock = pygame.time.Clock()

    title_font = pygame.font.Font(None, 72)
    button_font = pygame.font.Font(None, 36)

    titulo_text = title_font.render("CYBER PURSUIT", True, (0, 200, 255))
    titulo_rect = titulo_text.get_rect(center=(ancho // 2, alto // 3))

    button_text = button_font.render("INICIAR JUEGO", True, (255, 255, 255))
    button_rect = button_text.get_rect(center=(ancho // 2, alto // 2))
    button_color = (0, 150, 255)
    button_hover_color = (0, 200, 255)

    running = True
    while running:
        pantalla.fill((10, 10, 30))

        for evento in pygame.event.get():
            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            elif evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                mouse_pos = pygame.mouse.get_pos()
                if button_rect.collidepoint(mouse_pos):
                    running = False

        mouse_pos = pygame.mouse.get_pos()
        color_actual = button_hover_color if button_rect.collidepoint(mouse_pos) else button_color

        pantalla.blit(titulo_text, titulo_rect)

        padding_x, padding_y = 20, 10
        button_bg_rect = pygame.Rect(
            button_rect.left - padding_x,
            button_rect.top - padding_y,
            button_rect.width + 2 * padding_x,
            button_rect.height + 2 * padding_y
        )
        pygame.draw.rect(pantalla, color_actual, button_bg_rect, border_radius=8)
        pantalla.blit(button_text, button_rect)

        pygame.display.flip()
        clock.tick(60)

def pantalla_game_over(pantalla, ancho, alto, victoria=False, puntos=0):
    """
    Muestra una pantalla de fin de juego (game over o victoria) con el puntaje final
    y un botón para salir del juego. Permite salir con un clic o pulsando ESC.

    Args:
        pantalla (pygame.Surface): Superficie donde se dibujan los elementos.
        ancho (int): Ancho de la pantalla.
        alto (int): Alto de la pantalla.
        victoria (bool): Si es True, se muestra mensaje de victoria. Si False, mensaje de derrota.
        puntos (int): Puntaje final del jugador.
    """
    pygame.font.init()
    clock = pygame.time.Clock()

    title_font = pygame.font.Font(None, 72)
    message_font = pygame.font.Font(None, 36)
    score_font = pygame.font.Font(None, 40)
    button_font = pygame.font.Font(None, 32)
    instr_font = pygame.font.Font(None, 24)

    if victoria:
        titulo_text = title_font.render("¡VICTORIA!", True, (0, 255, 0))
        mensaje = "Todos los enemigos eliminados"
    else:
        titulo_text = title_font.render("GAME OVER", True, (255, 0, 0))
        mensaje = "Has sido derrotado"

    mensaje_text = message_font.render(mensaje, True, (255, 255, 255))
    puntos_text = score_font.render(f"PUNTOS: {puntos}", True, (255, 255, 0))
    button_text = button_font.render("Salir", True, (255, 255, 255))
    instr_text = instr_font.render("Presiona ESC o haz clic para salir", True, (180, 180, 180))

    spacing = 40
    current_y = alto // 3

    titulo_rect = titulo_text.get_rect(center=(ancho // 2, current_y))
    current_y += spacing
    mensaje_rect = mensaje_text.get_rect(center=(ancho // 2, current_y))
    current_y += spacing
    puntos_rect = puntos_text.get_rect(center=(ancho // 2, current_y))
    current_y += spacing + 10

    padding_x = 100
    padding_y = 12

    button_text_rect = button_text.get_rect()
    button_bg_rect = pygame.Rect(0, 0, button_text_rect.width + 2 * padding_x, button_text_rect.height + 2 * padding_y)
    button_bg_rect.center = (ancho // 2, current_y)

    button_rect = button_text.get_rect(center=button_bg_rect.center)
    instr_rect = instr_text.get_rect(center=(ancho // 2, alto - 50))

    button_color = (180, 30, 30)
    button_hover_color = (230, 50, 50)

    running = True
    while running:
        pantalla.fill((10, 10, 30))

        for evento in pygame.event.get():
            if evento.type == pygame.MOUSEBUTTONDOWN and evento.button == 1:
                if button_bg_rect.collidepoint(pygame.mouse.get_pos()):
                    pygame.quit()
                    sys.exit()

            if evento.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            elif evento.type == pygame.KEYDOWN:
                if evento.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()

        mouse_pos = pygame.mouse.get_pos()
        hover = button_bg_rect.collidepoint(mouse_pos)
        color_actual = button_hover_color if hover else button_color

        pantalla.blit(titulo_text, titulo_rect)
        pantalla.blit(mensaje_text, mensaje_rect)
        pantalla.blit(puntos_text, puntos_rect)

        pygame.draw.rect(pantalla, color_actual, button_bg_rect, border_radius=8)
        pantalla.blit(button_text, button_rect)
        pantalla.blit(instr_text, instr_rect)

        pygame.display.flip()
        clock.tick(60)
