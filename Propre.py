import time
import pygame
from pygame.locals import KEYDOWN, QUIT, MOUSEBUTTONDOWN, K_RETURN, K_ESCAPE
import sys
from pygame.math import Vector2
import random
from _operator import attrgetter, methodcaller

# in seconds
MAX_TIME = 20

MAX_STAGNATION = 3000


def rotate(lst, x):
    lst[:] = lst[-x:] + lst[:-x]


def cross_between(sol_a, sol_b, cross_point_a, cross_point_b, cut_size=3):
    """
    OX operator between 2 solutions
    Help here :
        http://stackoverflow.com/questions/11782881/how-to-implement-ordered-crossover
        http://www.dmi.unict.it/mpavone/nc-cs/materiale/moscato89.pdf
    :param sol_a:
    :param sol_b:
    :param cut_size:
    :return: the 2 crossed children
    """

    # Creates our children, with the sub cities between the 2 cutting points
    child_a, child_b = sol_a.path[cross_point_a:cross_point_b], sol_b.path[cross_point_a:cross_point_b]

    size = len(sol_a)

    for i in range(size):
        current_city_ix = (cross_point_b + i) % size

        current_a_from_parent, current_b_from_parent = sol_a.path[current_city_ix], sol_b.path[current_city_ix]

        # Is the current city from b parent in a child ?
        if current_b_from_parent not in child_a:
            child_a.append(current_b_from_parent)

        # Is the current city from a parent in b child ?
        if current_a_from_parent not in child_b:
            child_b.append(current_a_from_parent)

    # Rotates the child, so the first city are inside the cutting points
    rotate(child_a, cross_point_a)
    rotate(child_b, cross_point_a)

    return Solution(sol_a.problem, child_a), Solution(sol_b.problem, child_b)


class Gui:
    def __init__(self):
        self.screen_x = 500
        self.screen_y = 500

        self.city_color = [10, 10, 200]  # blue
        self.city_radius = 3

        self.font_color = [255, 255, 255]  # white

        pygame.init()
        self.window = pygame.display.set_mode((self.screen_x, self.screen_y))
        pygame.display.set_caption('Exemple')
        self.screen = pygame.display.get_surface()
        self.font = pygame.font.Font(None, 30)

        pygame.event.wait()

    def wait(self):
        while True:
            for event in pygame.event.get():
                if event.type == QUIT or (event.type == KEYDOWN and event.key == K_RETURN):
                    return

    def get_cities(self):
        cities = []
        self.draw(cities)

        collecting = True

        while collecting:
            for event in pygame.event.get():
                if event.type == QUIT:
                    sys.exit(0)
                elif event.type == KEYDOWN and event.key == K_RETURN:
                    collecting = False
                elif event.type == MOUSEBUTTONDOWN:
                    cities.append(pygame.mouse.get_pos())
                    self.draw(cities)

        self.screen.fill(0)
        pygame.draw.lines(self.screen, self.city_color, True, cities)
        text = self.font.render("Un chemin, pas le meilleur!", True, self.font_color)
        textRect = text.get_rect()
        self.screen.blit(text, textRect)
        pygame.display.flip()

        return cities

    def draw(self, positions, draw_lines=False):
        self.screen.fill(0)
        for pos in positions:
            pygame.draw.circle(self.screen, self.city_color, pos, self.city_radius)
        if len(positions) > 1 and draw_lines:
            pygame.draw.lines(self.screen, self.city_color, True, positions)

        text = self.font.render("Nombre: %i" % len(positions), True, self.font_color)
        textRect = text.get_rect()
        self.screen.blit(text, textRect)
        pygame.display.flip()

    def send_solution(self, solution):
        self.solution = [(int(city.x), int(city.y)) for city in solution]
        self.draw(self.solution, draw_lines=True)


class Population:
    EVOLUTION_STEP_PERCENTAGE = 0.4
    MUTATION_PERCENTAGE = 0.35

    def __init__(self, solutions=[]):
        self.solutions = solutions
        self.best_solution = None
        self.cut_a = int(len(self.solutions[0]) * 0.25)
        self.cut_b = int(len(self.solutions[0]) * 0.75)
        self.sorted = False

    def __str__(self):
        return str(self.solutions)

    def selection(self):
        selected_size = int(len(self.solutions) * self.EVOLUTION_STEP_PERCENTAGE)

        if not self.sorted:
            self.solutions = sorted(self.solutions, key=attrgetter('fitness'))[:selected_size]
        else:
            self.solutions = self.solutions[:selected_size]

    def crossover(self):
        children = []
        choices = self.solutions

        for sol_ix in range(len(self.solutions)):
            child_a, child_b = cross_between(self.solutions[sol_ix], self.solutions[(sol_ix + 1) % len(self.solutions)],
                                             self.cut_a, self.cut_b)
            children.append(child_a)
            children.append(child_b)
        self.solutions = children

    def mutation(self):
        n = int(len(self.solutions) * self.MUTATION_PERCENTAGE)
        indexes = random.sample(range(0, len(self.solutions)), n)
        for ix in indexes:
            self.solutions.append(self.solutions[ix].reverse_mutate())
        self.sorted = False

    def find_best_solution(self):
        if len(self.solutions) > 0:
            self.solutions = sorted(self.solutions, key=attrgetter('fitness'))
            self.best_solution = self.solutions[0]
            self.sorted = True
        else:
            return self.best_solution


class Problem:
    def __init__(self, cities={}):
        self.cities = cities

    def __len__(self):
        return len(self.cities)

    def __iter__(self):
        return self.cities.items().__iter__()

    def create_solution(self):
        path = list(self.cities.keys())
        random.shuffle(path)
        return Solution(problem=self, path=path)


class Solution(object):
    indexes = [random.randrange(0, 20) for _ in range(20)]
    current_index = 0

    def __init__(self, problem, path=[]):
        self.problem = problem
        self.path = path
        self.fitness = 0
        self.compute_fitness()

    def __len__(self):
        return len(self.path)

    def __iter__(self):
        return [self.problem.cities[city_name] for city_name in self.path].__iter__()

    def __str__(self):
        return "%s : %s" % (str(self.fitness), str(self.path))

    def reverse_mutate(self):
        city_a, city_b = random.sample(range(0, len(self.path)), 2)
        return Solution(problem=self.problem, path=self.reverse_sublist(self.path, city_a, city_b))

    def reverse_sublist(self, lst, start, end):
        lst[start:end] = lst[start:end][::-1]
        return lst

    def compute_fitness(self):
        total = 0
        last_city = self.problem.cities[self.path[0]]
        for city_name in self.path[1:]:
            current = self.problem.cities[city_name]
            total += current.pos.distance_to(last_city.pos)
            last_city = current
        total += last_city.pos.distance_to(self.problem.cities[self.path[0]].pos)
        self.fitness = total


class City:
    def __init__(self, name, x, y):
        self.name = name
        self.x = float(x)
        self.y = float(y)
        self.pos = Vector2(float(x), float(y))

    def __str__(self, *args, **kwargs):
        return "%s x: %s y: %s" % (self.name, self.x, self.y)


def import_cities_from_file(file):
    with open(file) as f:
        return {line.split()[0]: City(*line.split()) for line in f}


def import_cities_from_gui(gui_data):
    return {'test %s %s' % (x, y): City('test %s %s' % (x, y), x, y) for x, y in gui_data}


def ga_solve(file=None, gui=True, maxtime=MAX_TIME):

    if gui:
        gui = Gui()
    else:
        gui = None

    MAX_TIME = maxtime

    if file is None:
        cities = import_cities_from_gui(gui.get_cities())
    else:
        cities = import_cities_from_file(file)

    problem = Problem(cities=cities)
    best_solution = evolution_loop(problem=problem, nb_solutions=20, gui=gui)

    if gui:
        gui.wait()

    return best_solution.fitness, best_solution.path


def evolution_loop(problem, nb_solutions, gui):
    # Create solutions
    solutions = []
    current_time_left = MAX_TIME
    current_stagnation = 0
    current_best_solution = None

    for i in range(nb_solutions):
        solutions.append(problem.create_solution())

    population = Population(solutions=solutions)

    while current_time_left > 0 and current_stagnation < MAX_STAGNATION:
        start_time = time.time()

        population.selection()
        population.crossover()
        population.mutation()
        last_solution = population.best_solution
        population.find_best_solution()

        elapsed_time = time.time() - start_time
        current_time_left -= elapsed_time

        if last_solution and last_solution.fitness == population.best_solution.fitness:
            current_stagnation += 1
        else:
            current_stagnation = 0

        if not current_best_solution or population.best_solution.fitness < current_best_solution.fitness:
            current_best_solution = population.best_solution

        #print(population.best_solution)
        if gui:
            gui.send_solution(population.best_solution)
    if gui:
        gui.send_solution(current_best_solution)

    #print(" BEST SOLUTION EVER BIIIM")
    #print(current_best_solution)

    return current_best_solution


if __name__ == "__main__":
    ga_solve(gui=True)
    #print(ga_solve(file='data/pb100.txt',maxtime=20,gui=False))
