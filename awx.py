import pygame
import random
import numpy as np
import sys

# --- КОНФИГУРАЦИЯ ---
WIDTH, HEIGHT = 1200, 800
FPS = 60
GRID_SIZE = 85 
CELL_SIZE = WIDTH // GRID_SIZE
ROWS = HEIGHT // CELL_SIZE

COLOR_BG = (5, 8, 20)
COLOR_GRID = (15, 25, 50)

TYPE_COLORS = {
    1: (50, 255, 100),   # Зеленый
    2: (100, 200, 255),  # Голубой
    3: (255, 60, 60),    # Красный
    4: (255, 250, 50),   # Желтый
    5: (140, 70, 20)     # Грибница
}

TYPE_DESC = {
    1: "ЗЕЛЕНЫЙ: Быстрый рост, боится Желтых, друг Грибницы",
    2: "ГОЛУБОЙ: Чистый, иммунитет к яду, ест старых Желтых",
    3: "КРАСНЫЙ: Охотник, сильно гадит, боится яда Желтых",
    4: "ЖЕЛТЫЙ: Санитар, ест яд, обжигает Зеленых",
    5: "ГРИБНИЦА: Убивает всех кроме Зеленых, пускает споры"
}

class Spore:
    def __init__(self, x, y):
        self.x, self.y = x, y
        angle = random.uniform(0, 2 * np.pi)
        speed = random.uniform(60, 150)
        self.vx, self.vy = np.cos(angle) * speed, np.sin(angle) * speed
        self.life = random.uniform(2.0, 5.0)

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0

class Bacteria:
    def __init__(self, gx, gy, b_type=1, hp=80):
        self.gx, self.gy = gx, gy
        self.type = b_type
        self.hp = hp
        self.age = 0
        self.max_life = 16.0 * random.uniform(0.8, 1.2)
        self.met_rate = {1:0.9, 2:0.5, 3:1.9, 4:0.7, 5:0.1}[b_type]

    def update(self, dt, food_map, waste_map, bacteria_dict, spores):
        if self.type == 5:
            food_map[int(self.gy), int(self.gx)] += dt * 8
            if random.random() < 0.001: 
                spores.append(Spore(self.gx * CELL_SIZE + CELL_SIZE//2, self.gy * CELL_SIZE + CELL_SIZE//2))
            return True

        self.age += dt
        if self.age > self.max_life: return False
        
        gx, gy = int(self.gx), int(self.gy)
        current_waste = waste_map[gy, gx]
        
        if self.type == 1:
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                pos = (gx+dx, gy+dy)
                if pos in bacteria_dict and bacteria_dict[pos].type == 4: self.hp -= 45 * dt 
        
        if self.type != 1: 
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                pos = (gx+dx, gy+dy)
                if pos in bacteria_dict and bacteria_dict[pos].type == 5: self.hp -= 120 * dt
        
        if self.type == 4:
            if current_waste > 1:
                amount = min(current_waste, dt * 85.0); waste_map[gy, gx] -= amount; self.hp += amount * 1.5
        else:
            toxic_mult = 1.0 if self.type == 2 else (7.0 if current_waste > 30 else 1.0)
            self.hp -= self.met_rate * toxic_mult * dt
            if self.type == 3: waste_map[gy, gx] += 12.0 * dt
            elif self.type == 1: waste_map[gy, gx] += 6.0 * dt

        take = min(food_map[gy, gx], dt * 22); self.hp += take * (2.4 if self.type == 2 else 1.2); food_map[gy, gx] -= take
        return self.hp > 0

    def reproduce(self, bacteria_dict):
        r_limit = 90 if self.type == 1 else (180 if self.type == 5 else 115)
        age_limit = 0.7 if self.type == 1 else (4.5 if self.type == 5 else 1.5)
        if self.hp > r_limit and self.age > age_limit:
            dirs = [(0,1), (1,0), (0,-1), (-1,0)]; random.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = self.gx + dx, self.gy + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < ROWS and (nx, ny) not in bacteria_dict:
                    self.hp -= 45; return Bacteria(nx, ny, self.type, 75)
        return None

def main():
    pygame.init(); screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock(); font = pygame.font.SysFont("Consolas", 15, bold=True)
    food_map = np.random.rand(ROWS, GRID_SIZE) * 45; waste_map = np.zeros((ROWS, GRID_SIZE))
    bacteria_dict = {}; spores = []; selected_type = 1; paused = False

    for x in range(GRID_SIZE): 
        bacteria_dict[(x, 0)] = Bacteria(x, 0, 5)
        bacteria_dict[(x, ROWS-1)] = Bacteria(x, ROWS-1, 5)

    while True:
        dt = 1.0 / FPS; screen.fill(COLOR_BG)
        for x in range(0, WIDTH, CELL_SIZE): pygame.draw.line(screen, COLOR_GRID, (x, 0), (x, HEIGHT), 1)
        for y in range(0, HEIGHT, CELL_SIZE): pygame.draw.line(screen, COLOR_GRID, (0, y), (WIDTH, y), 1)

        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in [pygame.K_1, pygame.K_2, pygame.K_3, pygame.K_4, pygame.K_5]: selected_type = int(event.unicode)
                if event.key == pygame.K_c: bacteria_dict.clear(); waste_map.fill(0); spores.clear()
                if event.key == pygame.K_SPACE: paused = not paused

        m_btns = pygame.mouse.get_pressed(); mx, my = pygame.mouse.get_pos(); mgx, mgy = mx // CELL_SIZE, my // CELL_SIZE
        if 0 <= mgx < GRID_SIZE and 0 <= mgy < ROWS:
            if m_btns[0] and (mgx, mgy) not in bacteria_dict: bacteria_dict[(mgx, mgy)] = Bacteria(mgx, mgy, selected_type)
            if m_btns[2] and (mgx, mgy) in bacteria_dict: del bacteria_dict[(mgx, mgy)]

        if not paused:
            food_map = np.clip(food_map + 7.5 * dt, 0, 100); waste_map = np.clip(waste_map - 0.03 * dt, 0, 100)
            for s in spores[:]:
                if not s.update(dt): spores.remove(s)
                else:
                    sgx, sgy = int(s.x // CELL_SIZE), int(s.y // CELL_SIZE)
                    if 0 <= sgx < GRID_SIZE and 0 <= sgy < ROWS:
                        t = bacteria_dict.get((sgx, sgy))
                        if not t or (t.type != 5 and t.type != 1):
                            bacteria_dict[(sgx, sgy)] = Bacteria(sgx, sgy, 5); spores.remove(s)

            new_borns = []
            dead_keys = [pos for pos, b in bacteria_dict.items() if not b.update(dt, food_map, waste_map, bacteria_dict, spores)]
            for k in dead_keys: del bacteria_dict[k]
            for b in list(bacteria_dict.values()):
                child = b.reproduce(bacteria_dict)
                if child and len(bacteria_dict) < 6000: new_borns.append(child)
            for nb in new_borns:
                if (nb.gx, nb.gy) not in bacteria_dict: bacteria_dict[(nb.gx, nb.gy)] = nb

        # Отрисовка
        for y in range(ROWS):
            for x in range(GRID_SIZE):
                if waste_map[y, x] > 5:
                    s = pygame.Surface((CELL_SIZE-1, CELL_SIZE-1)); s.set_alpha(int(min(waste_map[y, x] * 4, 180))); s.fill((160, 0, 200)); screen.blit(s, (x*CELL_SIZE, y*CELL_SIZE))

        for b in bacteria_dict.values():
            cx, cy = b.gx * CELL_SIZE + CELL_SIZE // 2, b.gy * CELL_SIZE + CELL_SIZE // 2
            if b.type == 5: pygame.draw.rect(screen, TYPE_COLORS[5], (b.gx*CELL_SIZE+1, b.gy*CELL_SIZE+1, CELL_SIZE-2, CELL_SIZE-2))
            else:
                lr = max(0.2, 1.0 - (b.age / b.max_life))
                color = [int(c * (0.5 + 0.5 * lr)) for c in TYPE_COLORS[b.type]]
                pygame.draw.circle(screen, color, (cx, cy), int((CELL_SIZE // 2 - 1) * (0.6 + lr * 0.4)))
        for s in spores: pygame.draw.circle(screen, (200, 150, 100), (int(s.x), int(s.y)), 3)

        # ПАНЕЛЬ УПРАВЛЕНИЯ
        pygame.draw.rect(screen, (20, 30, 60), (0, 0, 520, 210))
        pygame.draw.rect(screen, (40, 50, 80), (0, 0, 520, 210), 2)
        pygame.draw.circle(screen, TYPE_COLORS[selected_type], (25, 25), 10)
        
        ctrl = [
            f"ВЫБРАН: {TYPE_DESC[selected_type]}",
            f"ПОПУЛЯЦИЯ: {len(bacteria_dict)} | {'ПАУЗА' if paused else 'ЖИЗНЬ'}",
            "--------------------------------------------------",
            "Кнопки 1-5: Смена типа бактерии",
            "ЛКМ: Сажать | ПКМ: Стирать | SPACE: Пауза | C: Сброс",
            "Зеленые и Грибница - союзники. Споры летят редко.",
            "Синие не гадят и чистят поле от старых Желтых."
        ]
        for i, text in enumerate(ctrl):
            color = (255, 255, 255) if i != 0 else TYPE_COLORS[selected_type]
            screen.blit(font.render(text, True, color), (45 if i==0 else 10, 15 + i * 25))
            
        pygame.display.flip(); clock.tick(FPS)

if __name__ == "__main__": main()
