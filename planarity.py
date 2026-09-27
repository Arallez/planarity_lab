"""Проверка планарности алгоритмом Демукрона и геометрическая укладка Тутте."""

import argparse
from pathlib import Path
import sys

from algorithms import (components, graph_edges, planar_embedding,
                        geometric_embedding, oriented_area, validate_drawing)


def read_graph(stream):
    """Первая строка: n m. Далее m строк u v; вершины имеют номера 1..n."""
    header = stream.readline().split()
    if len(header) != 2:
        raise ValueError('Первая строка должна содержать n и m.')
    n, m = map(int, header)
    if n < 1 or m < 0:
        raise ValueError('Нужно n >= 1 и m >= 0.')
    if m > n * (n - 1) // 2:
        raise ValueError('Слишком много рёбер для простого графа.')
    graph = {v: set() for v in range(1, n + 1)}
    for i in range(m):
        row = stream.readline().split()
        if len(row) != 2:
            raise ValueError(f'Ребро {i + 1}: нужны два номера вершин.')
        u, v = map(int, row)
        if u not in graph or v not in graph:
            raise ValueError(f'Номера вершин должны быть от 1 до {n}.')
        if u == v:
            raise ValueError('Петли не поддерживаются.')
        if v in graph[u]:
            raise ValueError(f'Ребро {u} {v} повторяется.')
        graph[u].add(v)
        graph[v].add(u)
    return graph


def make_report(graph, rotation, positions, details):
    n, m, c = len(graph), len(graph_edges(graph)), len(components(graph))
    lines = [f'Вершин: {n}', f'Рёбер: {m}', f'Компонент связности: {c}',
             'Проверка планарности: собственная реализация алгоритма Демукрона.']
    if rotation is None:
        return '\n'.join(lines + ['Граф непланарен.',
                                  'Найден сегмент без допустимой грани. Подробности в файле шагов.',
                                  'Плоская геометрическая укладка невозможна.'])
    lines.extend(['Граф планарен.', 'Геометрическая укладка: триангуляция и метод Тутте.',
                  'Система уравнений решена методом Гаусса в точных дробях.',
                  'Проверка координат: совпадений и пересечений нет.', '',
                  'Циклический порядок соседей против часовой стрелки:'])
    for v in sorted(rotation):
        lines.append(f'{v}: ' + (' '.join(map(str, rotation[v])) or 'нет соседей'))

    total_faces = 1
    for index, detail in enumerate(details, 1):
        faces = detail['faces']
        outer = max(range(len(faces)), key=lambda i: oriented_area(faces[i], positions))
        total_faces += len(faces) - 1
        lines.extend(['', f'Компонента {index}: {detail["vertices"]}',
                      'Грани исходного графа (обходы замкнуты):'])
        for i, face in enumerate(faces):
            label = ' — внешняя' if i == outer else ''
            lines.append(f'F{i + 1}{label}: ' + ' '.join(map(str, face)))
        if detail['outer_triangle']:
            lines.append(f'Добавленные для триангуляции рёбра: {detail["added_edges"]}')
            lines.append(f'Внешний треугольник дополненного графа: {detail["outer_triangle"]}')
        else:
            lines.append('Одна или две вершины: координаты заданы непосредственно.')
    lines.extend(['', f'Всего граней с общей внешней: {total_faces}',
                  f'Формула Эйлера: n - m + f = {n - m + total_faces} = 1 + c = {1 + c}.',
                  '', 'Точные координаты вершин:'])
    for v in sorted(positions):
        x, y = positions[v]
        lines.append(f'{v}: ({x}, {y})')
    return '\n'.join(lines)


def draw_graph(graph, positions, output):
    """Matplotlib только проводит отрезки по уже вычисленным координатам."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    # Алгоритмы работают с точными дробями. Float используется только для PNG.
    points = {v: (float(x), float(y)) for v, (x, y) in positions.items()}
    width = min(20, max(8, 4 * len(components(graph))))
    fig, ax = plt.subplots(figsize=(width, 7))
    for u, v in sorted(graph_edges(graph)):
        ax.plot([points[u][0], points[v][0]], [points[u][1], points[v][1]],
                color='black', linewidth=1.3, zorder=1)
    vertices = sorted(graph)
    ax.scatter([points[v][0] for v in vertices], [points[v][1] for v in vertices],
               s=360, facecolors='white', edgecolors='black', linewidths=1.3, zorder=2)
    for v, (x, y) in points.items():
        ax.text(x, y, str(v), ha='center', va='center', fontsize=10, zorder=3)
    ax.set_title('Плоская укладка: Демукрон + Тутте')
    ax.set_aspect('equal')
    ax.margins(0.15)
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(output, dpi=200)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', nargs='?', type=Path, help='файл графа; без него — ввод с клавиатуры')
    parser.add_argument('--out', type=Path, default=Path('results'), help='папка результатов')
    parser.add_argument('--steps', action='store_true', help='показать шаги Демукрона в консоли')
    args = parser.parse_args()
    try:
        if args.input:
            with args.input.open(encoding='utf-8-sig') as stream:
                graph = read_graph(stream)
                if stream.read().strip():
                    raise ValueError('После m рёбер в файле есть лишние данные.')
        else:
            print('Введите n m, затем m строк u v:')
            graph = read_graph(sys.stdin)
        rotation, log = planar_embedding(graph)
        positions, details = {}, []
        if rotation is not None:
            positions, details = geometric_embedding(graph, rotation)
            validate_drawing(graph, positions)
        report = make_report(graph, rotation, positions, details)
        if args.steps:
            print('\n'.join(log) + '\n')
        print(report)
        args.out.mkdir(parents=True, exist_ok=True)
        name = args.input.stem if args.input else 'graph'
        report_path = args.out / f'{name}_result.txt'
        steps_path = args.out / f'{name}_steps.txt'
        report_path.write_text(report + '\n', encoding='utf-8')
        steps_path.write_text('\n'.join(log) + '\n', encoding='utf-8')
        print(f'\nРезультат: {report_path}\nШаги Демукрона: {steps_path}')
        if rotation is not None:
            image_path = args.out / f'{name}_planar.png'
            draw_graph(graph, positions, image_path)
            print(f'Рисунок: {image_path}')
        else:
            print('Рисунок не создавался. Ранее сохранённые PNG не обновляются.')
    except (ValueError, OSError, RuntimeError) as error:
        print(f'Ошибка: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
