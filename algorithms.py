"""Демукрон, триангуляция и укладка Тутте без графовых библиотек."""

from collections import deque
from fractions import Fraction
from itertools import combinations


def edge(u, v):
    return (min(u, v), max(u, v))


def graph_edges(graph):
    return {edge(u, v) for u in graph for v in graph[u]}


def from_edges(edges):
    graph = {}
    for u, v in sorted(edges):
        graph.setdefault(u, set()).add(v)
        graph.setdefault(v, set()).add(u)
    return graph


def components(graph):
    """Компоненты связности, включая изолированные вершины."""
    unseen = set(graph)
    result = []
    while unseen:
        start = min(unseen)
        unseen.remove(start)
        stack, vertices = [start], {start}
        while stack:
            u = stack.pop()
            for v in sorted(graph[u]):
                if v in unseen:
                    unseen.remove(v)
                    vertices.add(v)
                    stack.append(v)
        result.append(vertices)
    return result


def biconnected_blocks(graph):
    """Блоки по рёбрам: собственный DFS с временами входа и low."""
    entered, low, parent = {}, {}, {}
    edge_stack, blocks = [], []
    for root in sorted(graph):
        if root in entered:
            continue
        entered[root] = low[root] = len(entered)
        parent[root] = None
        stack = [(root, iter(sorted(graph[root])))]
        while stack:
            u, neighbors = stack[-1]
            v = next(neighbors, None)
            if v is None:
                stack.pop()
                p = parent[u]
                if p is not None:
                    low[p] = min(low[p], low[u])
                    if low[u] >= entered[p]:
                        block = set()
                        while True:
                            a, b = edge_stack.pop()
                            block.add(edge(a, b))
                            if (a, b) == (p, u):
                                break
                        blocks.append(block)
            elif v == parent[u]:
                continue
            elif v not in entered:
                parent[v] = u
                entered[v] = low[v] = len(entered)
                edge_stack.append((u, v))
                stack.append((v, iter(sorted(graph[v]))))
            elif entered[v] < entered[u]:
                low[u] = min(low[u], entered[v])
                edge_stack.append((u, v))
    return sorted(blocks, key=lambda block: min(block))


def find_path(graph, start, targets):
    """BFS до первого контакта; внутренние вершины пути не контакты."""
    queue = deque([start])
    parent = {start: None}
    while queue:
        u = queue.popleft()
        for v in sorted(graph[u]):
            if v in parent:
                continue
            parent[v] = u
            if v in targets:
                path = [v]
                while parent[path[-1]] is not None:
                    path.append(parent[path[-1]])
                return path[::-1]
            queue.append(v)
    raise RuntimeError('Не найден путь между контактными вершинами.')


def get_segments(graph, placed_vertices, placed_edges):
    """Сегменты относительно H: хорды и компоненты G - V(H) с контактами."""
    segments = []
    for u, v in sorted(graph_edges(graph) - placed_edges):
        if u in placed_vertices and v in placed_vertices:
            segments.append(({(u, v)}, {u, v}))

    outside = {u: graph[u] - placed_vertices for u in graph if u not in placed_vertices}
    for vertices in components(outside):
        edges, contacts = set(), set()
        for u in vertices:
            for v in graph[u]:
                edges.add(edge(u, v))
                if v in placed_vertices:
                    contacts.add(v)
        segments.append((edges, contacts))
    return segments


def split_face(face, path):
    """Цепь между двумя вершинами простой грани разбивает её на две."""
    i, j = face.index(path[0]), face.index(path[-1])
    if i > j:
        i, j = j, i
        path = path[::-1]
    first = face[i:j + 1] + path[-2:0:-1]
    second = face[j:] + face[:i + 1] + path[1:-1]
    return first, second


def demoucron(block, log):
    """Алгоритм Демукрона для двусвязного блока; None означает непланарность."""
    graph = from_edges(block)
    if len(block) == 1:
        u, v = next(iter(block))
        log.append(f'Мост {u}–{v}: одна грань.')
        return [[u, v]]

    # В двусвязном блоке ребро лежит на цикле: после его удаления
    # между концами остаётся путь. Добавление ребра замыкает этот путь.
    u, v = min(block)
    without_edge = {x: set(neighbors) for x, neighbors in graph.items()}
    without_edge[u].remove(v)
    without_edge[v].remove(u)
    cycle = find_path(without_edge, u, {v})
    faces = [cycle, cycle[::-1]]
    placed_vertices = set(cycle)
    placed_edges = {edge(a, b) for a, b in zip(cycle, cycle[1:] + cycle[:1])}
    log.append('Начальный цикл: ' + ' '.join(map(str, cycle + cycle[:1])))
    step = 0
    while placed_edges != block:
        step += 1
        segments = get_segments(graph, placed_vertices, placed_edges)
        face_vertices = [set(face) for face in faces]
        choices = []
        log.append(f'Шаг {step}. Грани: ' + '; '.join(
            f'F{i + 1}={face}' for i, face in enumerate(faces)))
        for i, (edges, contacts) in enumerate(segments):
            admissible = [j for j, vertices in enumerate(face_vertices) if contacts <= vertices]
            log.append(f'  Сегмент {i + 1}: рёбра {sorted(edges)}, '
                       f'контакты {sorted(contacts)}, грани {[j + 1 for j in admissible]}.')
            if not admissible:
                log.append('Нет допустимой грани для сегмента. Блок непланарен.')
                return None
            choices.append(admissible)
        # Сначала сегмент с единственной гранью; иначе любой.
        chosen = min(range(len(segments)), key=lambda i: (len(choices[i]), i))
        edges, contacts = segments[chosen]
        if len(contacts) < 2:
            raise RuntimeError('В двусвязном блоке у сегмента менее двух контактов.')
        start = min(contacts)
        path = find_path(from_edges(edges), start, contacts - {start})
        face_index = choices[chosen][0]
        first, second = split_face(faces[face_index], path)
        faces[face_index] = first
        faces.append(second)
        placed_vertices.update(path)
        placed_edges.update(edge(a, b) for a, b in zip(path, path[1:]))
        log.append(f'  Укладываем цепь {path} в F{face_index + 1}.')
    log.append('Все рёбра блока уложены.')
    return faces


def rotation_from_faces(faces):
    """Из последовательных троек в обходах граней восстанавливаем вращение."""
    successor = {}
    for face in faces:
        for i, v in enumerate(face):
            previous, following = face[i - 1], face[(i + 1) % len(face)]
            successor.setdefault(v, {})[previous] = following
    rotation = {}
    for v, next_neighbor in successor.items():
        start = min(next_neighbor)
        order, current = [], start
        while current not in order:
            order.append(current)
            current = next_neighbor[current]
        if current != start or len(order) != len(next_neighbor):
            raise RuntimeError('Некорректная система вращения блока.')
        rotation[v] = order
    return rotation


def face_walks(rotation):
    """Каждое полуребро принадлежит ровно одному ориентированному обходу."""
    following = {v: {u: order[(i + 1) % len(order)] for i, u in enumerate(order)}
                 for v, order in rotation.items()}
    visited, faces = set(), []
    for u in sorted(rotation):
        if not rotation[u]:
            faces.append([u])
        for v in rotation[u]:
            if (u, v) in visited:
                continue
            start, current, face = (u, v), (u, v), []
            while current not in visited:
                a, b = current
                visited.add(current)
                face.append(a)
                current = (b, following[b][a])
            if current != start:
                raise RuntimeError('Некорректный обход грани.')
            faces.append(face)
    return faces


def planar_embedding(graph):
    """Разложение на блоки, Демукрон и склейка в точках сочленения."""
    rotation = {v: [] for v in graph}
    blocks = biconnected_blocks(graph)
    log = [f'Блоков с рёбрами: {len(blocks)}.']
    for index, block in enumerate(blocks, 1):
        log.append(f'\nБлок {index}: {sorted(block)}')
        faces = demoucron(block, log)
        if faces is None:
            return None, log
        local = rotation_from_faces(faces)
        # Блоки пересекаются только в точках сочленения. Соседи каждого
        # блока образуют непрерывную группу в общем циклическом порядке.
        for v, neighbors in local.items():
            rotation[v].extend(neighbors)
    for vertices in components(graph):
        local = {v: rotation[v] for v in vertices}
        m = sum(len(graph[v]) for v in vertices) // 2
        if len(vertices) - m + len(face_walks(local)) != 2:
            raise RuntimeError('Укладка не удовлетворяет формуле Эйлера.')
    return rotation, log


def triangulate(graph, faces):
    """Добавляем отсутствующие диагонали внутри граней, включая внешнюю.

    Обходы могут повторять точки сочленения и мосты. Концы новой
    диагонали всегда различны и ещё не смежны. Исходный граф не меняется.
    """
    augmented = {v: set(neighbors) for v, neighbors in graph.items()}
    triangles = [list(face) for face in faces]
    added = []
    index = 0
    while index < len(triangles):
        face = triangles[index]
        if len(face) == 3:
            index += 1
            continue
        diagonal = None
        for i in range(len(face)):
            for j in range(i + 2, len(face)):
                u, v = face[i], face[j]
                if (i == 0 and j == len(face) - 1) or u == v or v in augmented[u]:
                    continue
                diagonal = (i, j)
                break
            if diagonal is not None:
                break
        if diagonal is None:
            raise RuntimeError('Не удалось триангулировать грань.')
        i, j = diagonal
        u, v = face[i], face[j]
        augmented[u].add(v)
        augmented[v].add(u)
        added.append(edge(u, v))
        triangles[index] = face[i:j + 1]
        triangles.append(face[j:] + face[:i + 1])
    if len(graph_edges(augmented)) != 3 * len(graph) - 6:
        raise RuntimeError('Триангуляция не является максимальным планарным графом.')
    return augmented, triangles, added


def gaussian_elimination(matrix, right):
    """Собственный метод Гаусса с двумя правыми частями и точными дробями."""
    n = len(matrix)
    rows = [[Fraction(value) for value in row + rhs] for row, rhs in zip(matrix, right)]
    for k in range(n):
        pivot = next((i for i in range(k, n) if rows[i][k]), None)
        if pivot is None:
            raise RuntimeError('Вырожденная система уравнений Тутте.')
        rows[k], rows[pivot] = rows[pivot], rows[k]
        for i in range(k + 1, n):
            if rows[i][k] == 0:
                continue
            factor = rows[i][k] / rows[k][k]
            rows[i][k] = Fraction(0)
            for j in range(k + 1, n + 2):
                rows[i][j] -= factor * rows[k][j]
    solution = [[Fraction(0), Fraction(0)] for _ in range(n)]
    for i in range(n - 1, -1, -1):
        for axis in (0, 1):
            total = sum(rows[i][j] * solution[j][axis] for j in range(i + 1, n))
            solution[i][axis] = (rows[i][n + axis] - total) / rows[i][i]
    return solution


def tutte_layout(graph, outer):
    """Фиксируем внешнюю треугольную грань; внутри p(v) — среднее соседей."""
    positions = dict(zip(outer, [(Fraction(0), Fraction(0)),
                                 (Fraction(2), Fraction(0)),
                                 (Fraction(1), Fraction(2))]))
    inner = sorted(set(graph) - set(outer))
    indices = {v: i for i, v in enumerate(inner)}
    matrix = [[0] * len(inner) for _ in inner]
    right = [[Fraction(0), Fraction(0)] for _ in inner]
    for v, i in indices.items():
        matrix[i][i] = len(graph[v])
        for u in graph[v]:
            if u in indices:
                matrix[i][indices[u]] -= 1
            else:
                right[i][0] += positions[u][0]
                right[i][1] += positions[u][1]
    for v, coordinates in zip(inner, gaussian_elimination(matrix, right)):
        positions[v] = tuple(coordinates)
    return positions


def geometric_embedding(graph, rotation):
    """Координаты всех компонент; вспомогательные рёбра нужны только для Тутте."""
    positions, details = {}, []
    offset = Fraction(0)
    for vertices in components(graph):
        local_graph = {v: graph[v] for v in vertices}
        local_rotation = {v: rotation[v] for v in vertices}
        faces = face_walks(local_rotation)
        added, outer = [], []
        if len(vertices) < 3:
            local = {v: (Fraction(i), Fraction(0)) for i, v in enumerate(sorted(vertices))}
        else:
            augmented, triangles, added = triangulate(local_graph, faces)
            outer = triangles[0]
            local = tutte_layout(augmented, outer)
        for v, (x, y) in local.items():
            positions[v] = (x + offset, y)
        offset += 4
        details.append({'vertices': sorted(vertices), 'faces': faces,
                        'added_edges': added, 'outer_triangle': outer})
    return positions, details


def oriented_area(face, positions):
    return sum(positions[u][0] * positions[v][1] - positions[v][0] * positions[u][1]
               for u, v in zip(face, face[1:] + face[:1]))


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def validate_drawing(graph, positions):
    """Точная проверка: разные вершины, нет вершин на чужих рёбрах и пересечений."""
    if len(set(positions.values())) != len(graph):
        raise RuntimeError('На рисунке совпали вершины.')
    edges = sorted(graph_edges(graph))
    for u, v in edges:
        a, b = positions[u], positions[v]
        for w, p in positions.items():
            if w in (u, v):
                continue
            if (cross(a, b, p) == 0 and min(a[0], b[0]) <= p[0] <= max(a[0], b[0])
                    and min(a[1], b[1]) <= p[1] <= max(a[1], b[1])):
                raise RuntimeError(f'Вершина {w} попала на ребро {u}–{v}.')
    for (u, v), (s, t) in combinations(edges, 2):
        if len({u, v, s, t}) < 4:
            continue
        a, b, c, d = (positions[x] for x in (u, v, s, t))
        if cross(a, b, c) * cross(a, b, d) < 0 and cross(c, d, a) * cross(c, d, b) < 0:
            raise RuntimeError(f'Пересеклись рёбра {u}–{v} и {s}–{t}.')
