# -*- coding: utf-8 -*- 
"""
GUI-версія мінімальної онтології "РОСЛИНИ":
- рівно 20+ класів;
- 3 відношення: is_a, part_of, grows_in;
- ієрархія класів;
- інстанси на кожен листовий клас;
- пошук шляху між поняттями.

Запуск: python plants_ontology.py
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Dict, Set, Tuple, List
import tkinter as tk
from tkinter import ttk, messagebox
import re

# ==========================================
# 1) КЛАСИ ТА ВІДНОШЕННЯ (БАЗА ЗНАНЬ)
# ==========================================

# is_a: (child_class, parent_class)
IS_A_EDGES: Set[Tuple[str, str]] = {
    ("організм", "сутність"),
    ("рослина", "організм"),

    ("насінні", "рослина"),
    ("покритонасінні", "насінні"),
    ("дводольні", "покритонасінні"),
    ("розові", "евдикоти"),
    ("троянда", "трояндові"),
    ("яблуня", "трояндові"),

    ("злаки", "покритонасінні"),
    ("пшениця", "злаки"),
    ("кукурудза", "злаки"),

    ("хвойні", "насінні"),
    ("сосна", "хвойні"),
    ("ялина", "хвойні"),

    ("орган_рослини", "сутність"),
    ("квітка", "орган_рослини"),
    ("плід", "орган_рослини"),
    ("насінина", "орган_рослини"),

    ("оселище", "сутність"),
}

# part_of: (part, whole)
PART_OF_EDGES: Set[Tuple[str, str]] = {
    ("квітка", "рослина"),
    ("плід", "рослина"),
    ("насінина", "плід"),
}

# grows_in: (plant_class, habitat)
GROWS_IN_EDGES: Set[Tuple[str, str]] = {
    ("сосна", "помірний_ліс"),
    ("ялина", "помірний_ліс"),
    ("пшениця", "степ"),
    ("кукурудза", "степ"),
    ("троянда", "помірний_ліс"),
    ("яблуня", "помірний_ліс"),
}

# instance mapping: instance_name -> class_name
INSTANCES: Dict[str, str] = {
    "rose_1": "троянда", "rose_2": "троянда",
    "apple_1": "яблуня", "apple_2": "яблуня",
    "wheat_1": "пшениця", "wheat_2": "пшениця",
    "maize_1": "кукурудза", "maize_2": "кукурудза",
    "pine_1": "сосна", "pine_2": "сосна",
    "spruce_1": "ялина", "spruce_2": "ялина",

    # оселища як інстанси класу "оселище"
    "temperate_forest": "оселище",
    "steppe": "оселище",
}

# 2) ІНДЕКСИ ДЛЯ is_a
ISA_CHILDREN_INDEX: Dict[str, Set[str]] = defaultdict(set)
ISA_PARENTS_INDEX: Dict[str, Set[str]] = defaultdict(set)
for child_class, parent_class in IS_A_EDGES:
    ISA_CHILDREN_INDEX[parent_class].add(child_class)
    ISA_PARENTS_INDEX[child_class].add(parent_class)

# 3) ПОБУДОВА ГРАФА З МІТКАМИ

def build_labeled_edges() -> List[Tuple[str, str, str]]:
    """Повертає список орієнтованих ребер (src, dst, label) для всіх відношень,
    включно з інверсіями, щоб пошук міг іти в обидва боки."""
    edges: List[Tuple[str, str, str]] = []

    # is_a та інверсія
    for child_class, parent_class in IS_A_EDGES:
        edges.append((child_class, parent_class, "is_a"))
        edges.append((parent_class, child_class, "is_a↑"))

    # part_of та інверсія (has_part)
    for part_node, whole_node in PART_OF_EDGES:
        edges.append((part_node, whole_node, "part_of"))
        edges.append((whole_node, part_node, "has_part"))

    # grows_in двоспрямовано
    for plant_class, habitat in GROWS_IN_EDGES:
        edges.append((plant_class, habitat, "grows_in"))
        edges.append((habitat, plant_class, "grows_in↑"))

    # class ⇄ instance
    for instance_name, class_name in INSTANCES.items():
        edges.append((instance_name, class_name, "instance"))
        edges.append((class_name, instance_name, "instance↑"))

    return edges

LABELED_EDGES: List[Tuple[str, str, str]] = build_labeled_edges()

# ==========================================
# 4) ЛОГІКА ВИСНОВКІВ ТА ПОШУКУ
# ==========================================

def normalize_id(text: str) -> str:
    """Нормалізує введений ідентифікатор."""
    return text.strip().strip('"').strip("'").lower().replace(" ", "_")


def is_subclass_of(child: str, parent: str) -> bool:
    """Повертає True, якщо child є підкласом parent (через 0+ кроків is_a)."""
    visited: Set[str] = set()
    queue: deque[str] = deque([child])

    while queue:
        current = queue.popleft()
        if current == parent:
            return True
        for direct_parent in ISA_PARENTS_INDEX.get(current, ()):
            if direct_parent not in visited:
                visited.add(direct_parent)
                queue.append(direct_parent)
    return False


def find_labeled_path(src: str, dst: str) -> List[Tuple[str, str | None]]:
    """Пошук найкоротшого шляху в графі. Повертає список кроків."""
    if src == dst:
        return [(src, None)]

    visited: Set[str] = {src}
    queue: deque[Tuple[str, List[Tuple[str, str | None]]]] = deque([(src, [])])

    while queue:
        current_node, acc = queue.popleft()
        for edge_src, edge_dst, edge_label in LABELED_EDGES:
            if edge_src != current_node or edge_dst in visited:
                continue
            new_path = acc + [(edge_src, edge_label)]
            if edge_dst == dst:
                return new_path + [(edge_dst, None)]
            visited.add(edge_dst)
            queue.append((edge_dst, new_path))

    return []


def explain_relationship(a: str, b: str) -> str:
    """Готує людиночитний опис зв'язку між a і b."""
    a_norm, b_norm = normalize_id(a), normalize_id(b)
    path = find_labeled_path(a_norm, b_norm)
    if not path:
        return f'Чи "{a_norm}" пов’язана з "{b_norm}"? — Ні, зв\'язку не знайдено.'

    nodes = [node for (node, _) in path]
    chain = " → ".join(nodes)
    
    # Словник для кращого відображення типів зв'язків
    label_ua = {
        "is_a": "є (вид->рід)",
        "is_a↑": "містить підклас",
        "part_of": "є частиною",
        "has_part": "має частину",
        "grows_in": "росте в",
        "grows_in↑": "є місцем зростання для",
        "instance": "є екземпляром",
        "instance↑": "має екземпляр",
    }

    steps: List[str] = []
    for i in range(len(path) - 1):
        x, lab = path[i]
        y = path[i + 1][0]
        steps.append(f"  {i + 1}) {x} --[{label_ua.get(lab, lab)}]--> {y}")

    return f'Чи "{a_norm}" пов’язана з "{b_norm}"? — Так.\n\nЛанцюжок: {chain}\n\nПокрокове пояснення:\n' + "\n".join(steps)


# Транзитивні перевірки для конкретних гіпотез

def is_part_of_transitive(part: str, whole: str) -> bool:
    part_norm, whole_norm = normalize_id(part), normalize_id(whole)
    visited: Set[str] = {part_norm}
    queue: deque[str] = deque([part_norm])

    while queue:
        current = queue.popleft()
        if current == whole_norm:
            return True
        for p, w in PART_OF_EDGES:
            if p == current and w not in visited:
                visited.add(w)
                queue.append(w)
    return False


def has_part_transitive(whole: str, part: str) -> bool:
    whole_norm, part_norm = normalize_id(whole), normalize_id(part)
    visited: Set[str] = {whole_norm}
    queue: deque[str] = deque([whole_norm])

    while queue:
        current = queue.popleft()
        if current == part_norm:
            return True
        for p, w in PART_OF_EDGES:
            if w == current and p not in visited:
                visited.add(p)
                queue.append(p)
    return False


def is_grows_in_direct(plant: str, habitat: str) -> bool:
    return (normalize_id(plant), normalize_id(habitat)) in GROWS_IN_EDGES


# ==========================================
# 5) ПАРСЕР ГІПОТЕЗ
# ==========================================
ALIASES: Dict[str, str] = {"живий": "організм", "жива": "організм", "живою": "організм"}

def evaluate_hypothesis(text: str) -> str:
    """Парсер тверджень українською."""
    t = text.strip()
    patterns = [
        (r'^\s*(.+?)\s+є\s+частиною\s+(.+?)\s*$', "part_of"),
        (r'^\s*(.+?)\s+частина\s+(.+?)\s*$', "part_of"),
        (r'^\s*(.+?)\s+має\s+частину\s+(.+?)\s*$', "has_part"),
        (r'^\s*у\s+(.+?)\s+є\s+(.+?)\s*$', "has_part"),
        (r'^\s*(.+?)\s+росте\s+в\s+(.+?)\s*$', "grows_in"),
        (r'^\s*(.+?)\s+росте\s+у\s+(.+?)\s*$', "grows_in"),
        (r'^\s*(.+?)\s+є\s+(.+?)\s*$', "is_a"),
    ]

    for pattern, kind in patterns:
        match = re.match(pattern, t, flags=re.IGNORECASE)
        if not match:
            continue
        a_raw, b_raw = match.groups()

        if kind == "part_of":
            ok = is_part_of_transitive(a_raw, b_raw)
            return (f'Гіпотеза: "{a_raw} є частиною {b_raw}" → ' +
                    ("Істина\n\n" + explain_relationship(a_raw, b_raw) if ok else "Хиба"))

        if kind == "has_part":
            ok = has_part_transitive(a_raw, b_raw)
            return (f'Гіпотеза: "{a_raw} має частину {b_raw}" → ' +
                    ("Істина\n\n" + explain_relationship(a_raw, b_raw) if ok else "Хиба"))

        if kind == "grows_in":
            ok = is_grows_in_direct(a_raw, b_raw)
            return (f'Гіпотеза: "{a_raw} росте в {b_raw}" → ' +
                    ("Істина\n\n" + explain_relationship(a_raw, b_raw) if ok else "Хиба"))

        if kind == "is_a":
            a_norm = normalize_id(a_raw)
            b_norm = normalize_id(b_raw)
            b_norm = ALIASES.get(b_norm, b_norm)
            a_class = INSTANCES.get(a_norm, a_norm)
            ok = (a_norm == b_norm) or is_subclass_of(a_norm, b_norm) or is_subclass_of(a_class, b_norm)
            return (f'Гіпотеза: "{a_raw} є {b_raw}" → ' +
                    ("Істина\n\n" + explain_relationship(a_raw, b_raw) if ok else "Хиба"))

    return ("Не розпізнав гіпотезу. Приклади:\n"
            "  троянда є дводольні\n"
            "  насінина частина плід\n"
            "  яблуня має частину квітка\n"
            "  пшениця росте в степ\n"
            "  троянда є живою")


# ==========================================
# 6) ГРАФІЧНИЙ ІНТЕРФЕЙС (GUI)
# ==========================================
class OntologyApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Онтологія 'Рослини' — Інтелектуальна система")
        self.geometry("860x560")
        self.minsize(760, 480)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # --- Вкладка 1: Гіпотези (Natural Language) ---
        self.tab_hypothesis = ttk.Frame(notebook)
        notebook.add(self.tab_hypothesis, text="Запити (Природна мова)")

        self.hypothesis_label = ttk.Label(
            self.tab_hypothesis,
            text=(
                "Введіть запит українською (напр.: 'троянда є дводольні', "
                "'насінина частина плід', 'пшениця росте в степ'):"
            ),
        )
        self.hypothesis_label.pack(anchor="w", padx=8, pady=(8, 4))

        self.hypothesis_entry = ttk.Entry(self.tab_hypothesis)
        self.hypothesis_entry.pack(fill="x", padx=8, pady=4)
        self.hypothesis_entry.bind("<Return>", lambda e: self.on_check_hypothesis())

        self.hypothesis_button = ttk.Button(
            self.tab_hypothesis, text="Аналізувати", command=self.on_check_hypothesis
        )
        self.hypothesis_button.pack(anchor="w", padx=8, pady=(4, 8))

        self.hypothesis_output = tk.Text(self.tab_hypothesis, height=18, wrap="word", font=("Consolas", 10))
        self.hypothesis_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # --- Вкладка 2: Конструктор зв'язків ---
        self.tab_relations = ttk.Frame(notebook)
        notebook.add(self.tab_relations, text="Конструктор зв'язків")

        form = ttk.Frame(self.tab_relations)
        form.pack(fill="x", padx=8, pady=8)

        ttk.Label(form, text="Об'єкт A:").grid(row=0, column=0, sticky="w")
        self.input_a = ttk.Entry(form, width=25)
        self.input_a.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(form, text="Об'єкт B:").grid(row=0, column=2, sticky="w")
        self.input_b = ttk.Entry(form, width=25)
        self.input_b.grid(row=0, column=3, padx=4, pady=2)

        self.btn_explain = ttk.Button(form, text="Знайти будь-який зв’язок (A -> ... -> B)", command=self.on_explain)
        self.btn_explain.grid(row=0, column=4, padx=6)

        # Кнопки швидких перевірок
        btn_frame = ttk.Frame(self.tab_relations)
        btn_frame.pack(fill="x", padx=8)

        self.btn_check_isa = ttk.Button(btn_frame, text="Перевірити is_a (А це Б?)", command=self.on_check_isa)
        self.btn_check_isa.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_check_partof = ttk.Button(btn_frame, text="Перевірити part_of (А частина Б?)", command=self.on_check_partof)
        self.btn_check_partof.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_check_haspart = ttk.Button(btn_frame, text="Перевірити has_part (А має Б?)", command=self.on_check_haspart)
        self.btn_check_haspart.pack(side="left", fill="x", expand=True, padx=2)

        self.btn_check_growsin = ttk.Button(btn_frame, text="Перевірити grows_in (А росте в Б?)", command=self.on_check_growsin)
        self.btn_check_growsin.pack(side="left", fill="x", expand=True, padx=2)

        self.relations_output = tk.Text(self.tab_relations, height=18, wrap="word", font=("Consolas", 10))
        self.relations_output.pack(fill="both", expand=True, padx=8, pady=8)

    # --- Обробники подій ---

    def on_check_hypothesis(self) -> None:
        text = self.hypothesis_entry.get().strip()
        if not text:
            messagebox.showinfo("Підказка", "Введіть текст гіпотези.")
            return
        self.hypothesis_output.delete("1.0", "end")
        self.hypothesis_output.insert("1.0", evaluate_hypothesis(text))

    def on_explain(self) -> None:
        a = self.input_a.get().strip()
        b = self.input_b.get().strip()
        if not a or not b:
            messagebox.showinfo("Підказка", "Заповніть поля A і B.")
            return
        self.relations_output.delete("1.0", "end")
        self.relations_output.insert("1.0", explain_relationship(a, b))

    def on_check_isa(self) -> None:
        self._run_check(lambda a, b: (
            (a == b) or 
            is_subclass_of(a, b) or 
            is_subclass_of(INSTANCES.get(a, a), b)
        ), "є")

    def on_check_partof(self) -> None:
        self._run_check(is_part_of_transitive, "є частиною")

    def on_check_haspart(self) -> None:
        self._run_check(has_part_transitive, "має частину")

    def on_check_growsin(self) -> None:
        self._run_check(is_grows_in_direct, "росте в")

    def _run_check(self, func, relation_name) -> None:
        a = normalize_id(self.input_a.get())
        b = normalize_id(self.input_b.get())
        if not a or not b:
            messagebox.showinfo("Підказка", "Заповніть поля A і B.")
            return
            
        ok = func(a, b)
        msg = f'Перевірка: "{a} {relation_name} {b}" → ' + ("ІСТИНА" if ok else "ХИБА")
        
        # Додаємо пояснення шляху, якщо це істина або якщо користувач хоче зрозуміти чому ні
        explanation = explain_relationship(a, b)
        
        full_msg = f"{msg}\n\nДеталі шляху:\n{explanation}"
        
        self.relations_output.delete("1.0", "end")
        self.relations_output.insert("1.0", full_msg)


if __name__ == "__main__":
    OntologyApp().mainloop()