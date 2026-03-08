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

FOOD_GAIN = 12.0  
REPRO_COST = 50   
MAX_AGE = 22.0    

TYPE_COLORS = {1: (50, 255, 100), 2: (100, 200, 255), 3: (255, 60, 60), 4: (255, 250, 50), 5: (140, 70, 20)}
TYPE_DESC = {
    1: "ЗЕЛЕНЫЙ: Рост, союз Грибницы",
    2: "ГОЛУБОЙ: Иммунитет к яду, ест Желтых",
    3: "КРАСНЫЙ: Живучий в яду охотник",
    4: "ЖЕЛТЫЙ: Санитар, поглощает токсины",
    5: "ГРИБНИЦА: Барьер, пускает споры"
}

class Spore:
    def __init__(self, x, y):
        self.x, self.y = x, y
        angle = random.uniform(0, 2 * np.pi)
        speed = random.uniform(40, 100)
        self.vx, self.vy = np.cos(angle) * speed, np.sin(angle) * speed
        self.life = random.uniform(3.0, 6.0)

    def update(self, dt):
        self.x += self.vx * dt; self.y += self.vy * dt
        self.life -= dt; return self.life > 0

class Bacteria:
    def __init__(self, gx, gy, b_type=1, hp=None):
        self.gx, self.gy = gx, gy
        self.type = b_type
        self.hp = hp if hp else (100 if b_type == 3 else 80)
        self.age = 0
        self.max_life = MAX_AGE * random.uniform(0.9, 1.1)
        self.met_rate = {1:0.6, 2:0.35, 3:1.2, 4:0.5, 5:0.05}[b_type]

    def update(self, dt, food_map, waste_map, bacteria_dict, spores):
        if self.type == 5:
            food_map[int(self.gy), int(self.gx)] += dt * 5
            if random.random() < 0.0008: 
                spores.append(Spore(self.gx * CELL_SIZE + CELL_SIZE//2, self.gy * CELL_SIZE + CELL_SIZE//2))
            return True

        self.age += dt
        if self.age > self.max_life: return False
        
        gx, gy = int(self.gx), int(self.gy)
        current_waste = waste_map[gy, gx]
        
        # Защита от яда
        if self.type == 4:
            if current_waste > 1:
                amount = min(current_waste, dt * 60.0); waste_map[gy, gx] -= amount; self.hp += amount * 1.3
        else:
            toxic_res = 2.0 if self.type == 3 else 6.0
            toxic_mult = 1.0 if self.type == 2 else (toxic_res if current_waste > 30 else 1.0)
            self.hp -= self.met_rate * toxic_mult * dt
            if self.type == 3: waste_map[gy, gx] += 9.0 * dt
            elif self.type == 1: waste_map[gy, gx] += 4.5 * dt

        # ПИТАНИЕ / КАННИБАЛИЗМ ПРИ ГОЛОДЕ
        food_available = food_map[gy, gx]
        if food_available > 2:
            take = min(food_available, dt * 16)
            self.hp += take * (2.2 if self.type == 2 else 1.1)
            food_map[gy, gx] -= take
        else:
            # Механика голода: тянем HP из соседей
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                pos = (gx+dx, gy+dy)
                if pos in bacteria_dict and bacteria_dict[pos] is not self:
                    target = bacteria_dict[pos]
                    if target.type != 5: # Грибницу есть нельзя
                        steal = dt * 10
                        target.hp -= steal
                        self.hp += steal * 0.5
                        break

        # Взаимодействия
        if self.type == 1:
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                pos = (gx+dx, gy+dy)
                if pos in bacteria_dict and bacteria_dict[pos].type == 4: self.hp -= 30 * dt 
        
        if self.type != 1: 
            for dx, dy in [(-1,0), (1,0), (0,-1), (0,1)]:
                pos = (gx+dx, gy+dy)
                if pos in bacteria_dict and bacteria_dict[pos].type == 5: self.hp -= 100 * dt

        return self.hp > 0

    def reproduce(self, bacteria_dict):
        r_limit = 100 if self.type == 1 else (220 if self.type == 5 else 125)
        age_limit = 1.2 if self.type == 1 else (6.0 if self.type == 5 else 2.5)
        if self.hp > r_limit and self.age > age_limit:
            dirs = [(0,1), (1,0), (0,-1), (-1,0)]; random.shuffle(dirs)
            for dx, dy in dirs:
                nx, ny = self.gx + dx, self.gy + dy
                if 0 <= nx < GRID_SIZE and 0 <= ny < ROWS and (nx, ny) not in bacteria_dict:
                    self.hp -= REPRO_COST; return Bacteria(nx, ny, self.type)
        return None

def main():
    pygame.init(); screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock(); font = pygame.font.SysFont("Consolas", 15, bold=True)
    food_map = np.random.rand(ROWS, GRID_SIZE) * 40; waste_map = np.zeros((ROWS, GRID_SIZE))
    bacteria_dict = {}; spores = []; selected_type = 1; paused = False

    for x in range(GRID_SIZE): 
        bacteria_dict[(x, 0)] = Bacteria(x, 0, 5); bacteria_dict[(x, ROWS-1)] = Bacteria(x, ROWS-1, 5)

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
            food_map = np.clip(food_map + 5.0 * dt, 0, 100); waste_map = np.clip(waste_map - 0.02 * dt, 0, 100)
            for s in spores[:]:
                if not s.update(dt): spores.remove(s)
                else:
                    sgx, sgy = int(s.x // CELL_SIZE), int(s.y // CELL_SIZE)
                    if 0 <= sgx < GRID_SIZE and 0 <= sgy < ROWS:
                        t = bacteria_dict.get((sgx, sgy))
                        if not t or (t.type != 5 and t.type != 1):
                            bacteria_dict[(sgx, sgy)] = Bacteria(sgx, sgy, 5); spores.remove(s)

            new_borns = []
            for pos, b in list(bacteria_dict.items()):
                if not b.update(dt, food_map, waste_map, bacteria_dict, spores): del bacteria_dict[pos]
                else:
                    child = b.reproduce(bacteria_dict)
                    if child and len(bacteria_dict) < 5500: new_borns.append(child)
            for nb in new_borns:
                if (nb.gx, nb.gy) not in bacteria_dict: bacteria_dict[(nb.gx, nb.gy)] = nb

        for y in range(ROWS):
            for x in range(GRID_SIZE):
                if waste_map[y, x] > 5:
                    s = pygame.Surface((CELL_SIZE-1, CELL_SIZE-1)); s.set_alpha(int(min(waste_map[y, x] * 3.5, 160))); s.fill((150, 0, 180)); screen.blit(s, (x*CELL_SIZE, y*CELL_SIZE))

        for b in bacteria_dict.values():
            cx, cy = b.gx * CELL_SIZE + CELL_SIZE // 2, b.gy * CELL_SIZE + CELL_SIZE // 2
            if b.type == 5: 
                pygame.draw.rect(screen, TYPE_COLORS[5], (b.gx*CELL_SIZE+1, b.gy*CELL_SIZE+1, CELL_SIZE-2, CELL_SIZE-2))
            else:
                lr = max(0.2, 1.0 - (b.age / b.max_life))
                color = [int(c * (0.55 + 0.45 * lr)) for c in TYPE_COLORS[b.type]]
                pygame.draw.circle(screen, color, (cx, cy), int((CELL_SIZE // 2 - 1) * (0.7 + lr * 0.3)))
        for s in spores: pygame.draw.circle(screen, (180, 120, 80), (int(s.x), int(s.y)), 3)

        pygame.draw.rect(screen, (20, 30, 60), (0, 0, 560, 210))
        pygame.draw.rect(screen, (50, 60, 100), (0, 0, 560, 210), 2)
        pygame.draw.circle(screen, TYPE_COLORS[selected_type], (25, 25), 10)
        ctrl = [f"ВЫБРАН: {TYPE_DESC[selected_type]}", f"ПОПУЛЯЦИЯ: {len(bacteria_dict)} | {'ПАУЗА' if paused else 'ЖИЗНЬ'}", "--------------------------------------------------", "1-5: Тип | ЛКМ: Сеять | ПКМ: Ластик | SPACE: Пауза | C: Сброс", "КАННИБАЛИЗМ: При отсутствии еды клетки едят соседей.", "КРАСНЫЕ: Получают меньше урона от яда."]
        for i, text in enumerate(ctrl):
            color = (230, 230, 250) if i != 0 else TYPE_COLORS[selected_type]
            screen.blit(font.render(text, True, color), (45 if i==0 else 10, 15 + i * 25))
        pygame.display.flip(); clock.tick(FPS)

if __name__ == "__main__": main()
