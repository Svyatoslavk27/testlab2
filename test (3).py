# -*- coding: utf-8 -*-
"""
GUI-версія онтології "РОСЛИНИ"

Властивості:
- рівно 20 класів
- 3 відношення: is_a, part_of, grows_in
- ≥4 рівні ієрархії
- ≥2 інстанси на кожен листовий клас рослин
- нетривіальні відповіді через аналіз ланцюжків зв’язків
"""

from __future__ import annotations
from collections import deque
from typing import Dict, Set, Tuple, List
import tkinter as tk
from tkinter import ttk, messagebox
import re

# =========================================================
# 1) КЛАСИ ТА ВІДНОШЕННЯ
# =========================================================

IS_A_EDGES: Set[Tuple[str, str]] = {
    ("організм", "сутність"),
    ("рослина", "організм"),

    ("насінні", "рослина"),
    ("покритонасінні", "насінні"),
    ("дводольні", "покритонасінні"),
    ("однодольні", "покритонасінні"),

    ("трояндові", "дводольні"),
    ("злаки", "однодольні"),
    ("хвойні", "насінні"),

    ("троянда", "трояндові"),
    ("яблуня", "трояндові"),

    ("пшениця", "злаки"),
    ("кукурудза", "злаки"),

    ("сосна", "хвойні"),
    ("ялина", "хвойні"),

    ("орган_рослини", "сутність"),
    ("квітка", "орган_рослини"),
    ("плід", "орган_рослини"),

    ("оселище", "сутність"),
}

PART_OF_EDGES: Set[Tuple[str, str]] = {
    ("квітка", "рослина"),
    ("плід", "рослина"),
}

GROWS_IN_EDGES: Set[Tuple[str, str]] = {
    ("сосна", "помірний_ліс"),
    ("ялина", "помірний_ліс"),
    ("троянда", "помірний_ліс"),
    ("яблуня", "помірний_ліс"),
    ("пшениця", "степ"),
    ("кукурудза", "степ"),
}

INSTANCES: Dict[str, str] = {
    "rose_1": "троянда", "rose_2": "троянда",
    "apple_1": "яблуня", "apple_2": "яблуня",
    "wheat_1": "пшениця", "wheat_2": "пшениця",
    "maize_1": "кукурудза", "maize_2": "кукурудза",
    "pine_1": "сосна", "pine_2": "сосна",
    "spruce_1": "ялина", "spruce_2": "ялина",
}

# =========================================================
# 2) ПОБУДОВА МІЧЕНОГО ГРАФА
# =========================================================

def build_edges() -> List[Tuple[str, str, str]]:
    edges = []
    for c, p in IS_A_EDGES:
        edges.append((c, p, "is_a"))
        edges.append((p, c, "is_a↑"))

    for part, whole in PART_OF_EDGES:
        edges.append((part, whole, "part_of"))
        edges.append((whole, part, "has_part"))

    for plant, habitat in GROWS_IN_EDGES:
        edges.append((plant, habitat, "grows_in"))
        edges.append((habitat, plant, "grows_in↑"))

    for inst, cls in INSTANCES.items():
        edges.append((inst, cls, "instance"))
        edges.append((cls, inst, "instance↑"))

    return edges


LABELED_EDGES = build_edges()

# =========================================================
# 3) ЛОГІКА ВИСНОВКІВ
# =========================================================

def normalize(text: str) -> str:
    return text.strip().lower().replace(" ", "_")

def find_path(src: str, dst: str) -> List[Tuple[str, str | None]]:
    if src == dst:
        return [(src, None)]

    visited = {src}
    queue = deque([(src, [])])

    while queue:
        node, path = queue.popleft()
        for a, b, label in LABELED_EDGES:
            if a == node and b not in visited:
                new_path = path + [(a, label)]
                if b == dst:
                    return new_path + [(b, None)]
                visited.add(b)
                queue.append((b, new_path))
    return []

def explain(a: str, b: str) -> str:
    a, b = normalize(a), normalize(b)
    path = find_path(a, b)

    if not path:
        return f'Чи "{a}" пов’язана з "{b}"? — Хиба.'

    steps = []
    for i in range(len(path) - 1):
        x, lab = path[i]
        y = path[i + 1][0]
        steps.append(f"{i+1}) {x} -({lab})-> {y}")

    chain = " → ".join(node for node, _ in path)
    return (
        f'Чи "{a}" пов’язана з "{b}"? — Істина.\n'
        f"Шлях: {chain}\n"
        f"Кроки:\n" + "\n".join(steps)
    )

# =========================================================
# 4) ПАРСЕР ГІПОТЕЗ
# =========================================================

def evaluate(text: str) -> str:
    t = text.strip()

    patterns = [
        (r'(.+?) є (.+)',),
        (r'(.+?) частина (.+)',),
        (r'(.+?) росте в (.+)',),
    ]

    if "частина" in t:
        a, b = t.split("частина")
        return explain(a, b)

    if "росте" in t:
        a, b = t.split("в")
        return explain(a, b)

    if "є" in t:
        a, b = t.split("є")
        return explain(a, b)

    return "Не розпізнав твердження."

# =========================================================
# 5) GUI
# =========================================================

class OntologyApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Онтологія «Рослини»")
        self.geometry("860x520")

        label = ttk.Label(self, text="Введіть гіпотезу (напр.: троянда є рослина)")
        label.pack(pady=6)

        self.entry = ttk.Entry(self)
        self.entry.pack(fill="x", padx=8)

        btn = ttk.Button(self, text="Перевірити", command=self.check)
        btn.pack(pady=6)

        self.output = tk.Text(self, height=22, wrap="word")
        self.output.pack(fill="both", expand=True, padx=8, pady=8)

    def check(self):
        text = self.entry.get()
        if not text:
            messagebox.showinfo("Підказка", "Введіть гіпотезу")
            return
        self.output.delete("1.0", "end")
        self.output.insert("1.0", evaluate(text))


if __name__ == "__main__":
    OntologyApp().mainloop()
