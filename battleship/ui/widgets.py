import pygame

from .theme import PANEL_BORDER, PANEL_FILL, TEXT, mix


def draw_text(surf, font, text, color, pos, anchor="topleft", shadow=None, alpha=255):
    img = font.render(text, True, color)
    if alpha < 255:
        img.set_alpha(alpha)
    rect = img.get_rect()
    setattr(rect, anchor, pos)
    if shadow:
        sh = font.render(text, True, shadow)
        if alpha < 255:
            sh.set_alpha(alpha)
        surf.blit(sh, rect.move(2, 2))
    surf.blit(img, rect)
    return rect


def wrap(font, text, width):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if font.size(trial)[0] <= width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_panel(surf, rect, fill=PANEL_FILL, border=PANEL_BORDER, radius=14, width=1):
    rect = pygame.Rect(rect)
    tmp = pygame.Surface(rect.size, pygame.SRCALPHA)
    pygame.draw.rect(tmp, fill, tmp.get_rect(), border_radius=radius)
    if border:
        pygame.draw.rect(tmp, border, tmp.get_rect(), width, border_radius=radius)
    surf.blit(tmp, rect.topleft)


KINDS = {
    "normal": ((38, 66, 104), (62, 104, 156)),
    "primary": ((28, 140, 112), (40, 186, 148)),
    "danger": ((150, 54, 60), (200, 76, 82)),
}


class Button:
    def __init__(self, rect, label, action, visible=lambda: True, enabled=lambda: True,
                 active=lambda: False, kind="normal"):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.action = action
        self.visible = visible
        self.enabled = enabled
        self.active = active
        self.kind = kind
        self.hover = 0.0

    def hit(self, pos):
        return self.visible() and self.enabled() and self.rect.collidepoint(pos)

    def update(self, mouse, dt):
        target = 1.0 if self.hit(mouse) else 0.0
        self.hover += (target - self.hover) * min(1.0, dt / 90.0)

    def draw(self, surf, fonts):
        base, hot = KINDS[self.kind]
        enabled = self.enabled()
        if not enabled:
            body = (30, 40, 58)
            text_color = (96, 112, 134)
        else:
            body = mix(base, hot, self.hover)
            if self.active():
                body = (44, 150, 214)
            text_color = TEXT
        rect = self.rect.move(0, -int(2 * self.hover)) if enabled else self.rect
        pygame.draw.rect(surf, (4, 8, 16), self.rect.move(0, 4), border_radius=10)
        pygame.draw.rect(surf, body, rect, border_radius=10)
        top = pygame.Rect(rect.x + 2, rect.y + 2, rect.w - 4, rect.h // 2)
        pygame.draw.rect(surf, mix(body, (255, 255, 255), 0.12), top, border_radius=9)
        pygame.draw.rect(surf, mix(body, (255, 255, 255), 0.35 if enabled else 0.08), rect, 2, border_radius=10)
        font = fonts.h2 if self.rect.h >= 56 else fonts.btn
        img = font.render(self.label, True, text_color)
        surf.blit(img, img.get_rect(center=rect.center))
