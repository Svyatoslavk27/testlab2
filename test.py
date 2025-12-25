# -*- coding: utf-8 -*-
"""
GUI-версія мінімальної онтології "РОСЛИНИ" (рефакторинг імен змінних/функцій):
- рівно 20 класів;
- 3 відношення: is_a, part_of, grows_in;
- ≥4 рівні ієрархії за is_a;
- 2+ інстанси на кожен листовий клас (рослина);
- відповіді формуються автоматичним аналізом зв'язків (шлях + пояснення).

Запуск: python plants_ontology_refactored.py
"""

from __future__ import annotations
from collections import defaultdict, deque
from typing import Dict, Set, Tuple, List
import tkinter as tk
from tkinter import ttk, messagebox
import re

#  1) КЛАСИ ТА ВІДНОШЕННЯ
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
# Зручно для швидкого підйому до батьків та спуску до дітей
ISA_CHILDREN_INDEX: Dict[str, Set[str]] = defaultdict(set)
ISA_PARENTS_INDEX: Dict[str, Set[str]] = defaultdict(set)
for child_class, parent_class in IS_A_EDGES:
    ISA_CHILDREN_INDEX[parent_class].add(child_class)
    ISA_PARENTS_INDEX[child_class].add(parent_class)

# 3) ПОБУДОВА МІЧЕНИХ РЕБЕР

def build_labeled_edges() -> List[Tuple[str, str, str]]:
    """Повертає список орієнтованих ребер (src, dst, label) для всіх відношень,
    включно з інверсіями, щоб пошук міг іти в обидва боки."""
    edges: List[Tuple[str, str, str]] = []

    # is_a та інверсія (для навігації в обидві сторони)
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

# 4) ЛОГІКА ВИСНОВКІВ

def normalize_id(text: str) -> str:
    """Нормалізує введений ідентифікатор: обрізає пробіли/лапки,
    знижує регістр, замінює пробіли на підкреслення."""
    return text.strip().strip('"').strip("'").lower().replace(" ", "_")


def is_subclass_of(child: str, parent: str) -> bool:
    """Повертає True, якщо child є підкласом parent (через 0+ кроків is_a)."""
    visited: Set[str] = set()
    queue: deque[str] = deque([child])

    while queue:
        current = queue.popleft()
        if current == parent:
            return True
        for direct_parent in ISA_PARENTS_INDEX.get(current, ()):  # рух вгору
            if direct_parent not in visited:
                visited.add(direct_parent)
                queue.append(direct_parent)
    return False


def is_leaf_class(class_name: str) -> bool:
    """Листовий клас — той, що не має підкласів (дітей) у is_a."""
    return len(ISA_CHILDREN_INDEX.get(class_name, ())) == 0


def get_practical_leaf_classes() -> List[str]:
    """Повертає відсортований список листових класів, які є підкласами "рослина"."""
    all_nodes = {c for c, _ in IS_A_EDGES} | {p for _, p in IS_A_EDGES}
    practical = [cls for cls in all_nodes if is_leaf_class(cls) and is_subclass_of(cls, "рослина")]
    return sorted(practical)


def find_labeled_path(src: str, dst: str) -> List[Tuple[str, str | None]]:
    """Пошук шляху в міченому графі. Повертає список (node, edge_label_from_node),
    де останній елемент має мітку None (на фініші). Порожній список — якщо шляху немає."""
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
    """Готує людиночитний опис зв'язку між a і b (або каже, що зв'язку немає)."""
    a_norm, b_norm = normalize_id(a), normalize_id(b)
    path = find_labeled_path(a_norm, b_norm)
    if not path:
        return f'Чи "{a_norm}" пов’язана з "{b_norm}"? — Хиба.'

    nodes = [node for (node, _) in path]
    chain = " → ".join(nodes)
    label_ua = {
        "is_a": "is_a (узагальнення)",
        "is_a↑": "is_a (спеціалізація)",
        "part_of": "part_of (частина→ціле)",
        "has_part": "has_part (ціле→частина)",
        "grows_in": "grows_in (росте_в)",
        "grows_in↑": "grows_in↑",
        "instance": "instance",
        "instance↑": "instance↑",
    }

    steps: List[str] = []
    for i in range(len(path) - 1):
        x, lab = path[i]
        y = path[i + 1][0]
        steps.append(f"  {i + 1}) {x} -({label_ua.get(lab, lab)})-> {y}")

    return f'Чи "{a_norm}" пов’язана з "{b_norm}"? — Істина.\nШлях: {chain}\nКроки:\n' + "\n".join(steps)


# Транзитивні перевірки для конкретних відношень

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


#5) ПЕРЕВІРКА ВИМОГ

def _max_depth_from(node: str) -> int:
    best_depth = 1
    for child in ISA_CHILDREN_INDEX.get(node, ()):  # DFS у глибину
        best_depth = max(best_depth, 1 + _max_depth_from(child))
    return best_depth


def get_requirements_report() -> str:
    classes: Set[str] = set()
    for child, parent in IS_A_EDGES:
        classes.add(child)
        classes.add(parent)

    depth = max(_max_depth_from("сутність"), _max_depth_from("рослина"))

    # Перевірка інстансів 2+ для кожного листового класу рослин
    lacking: List[Tuple[str, int]] = []
    for leaf in get_practical_leaf_classes():
        count = sum(1 for v in INSTANCES.values() if v == leaf)
        if count < 2:
            lacking.append((leaf, count))

    return (
        f"К-ть класів: {len(classes)} (має бути рівно 20)\n"
        f"Відношення: is_a={len(IS_A_EDGES)}, part_of={len(PART_OF_EDGES)}, grows_in={len(GROWS_IN_EDGES)} (мають існувати всі 3)\n"
        f"Глибина is_a: {depth} (має бути ≥4)\n"
        f"Інстанси листових: {'OK' if not lacking else 'нестача: ' + str(lacking)}"
    )


# 6) ПАРСЕР ГІПОТЕЗ
ALIASES: Dict[str, str] = {"живий": "організм", "жива": "організм", "живою": "організм"}


def evaluate_hypothesis(text: str) -> str:
    """Простий парсер тверджень українською і перевірка відповідних відношень."""
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
            a_class = INSTANCES.get(a_norm, a_norm)  # інстанс → клас (якщо треба)
            ok = (a_norm == b_norm) or is_subclass_of(a_norm, b_norm) or is_subclass_of(a_class, b_norm)
            return (f'Гіпотеза: "{a_raw} є {b_raw}" → ' +
                    ("Істина\n\n" + explain_relationship(a_raw, b_raw) if ok else "Хиба"))

    return ("Не розпізнав гіпотезу. Приклади:\n"
            "  троянда є дводольні\n"
            "  насінина частина плід\n"
            "  яблуня має частину квітка\n"
            "  пшениця росте в степ\n"
            "  троянда є живою")


# 7) GUI
class OntologyApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("Онтологія 'Рослини' — гіпотези та зв’язки (refactored)")
        self.geometry("860x560")
        self.minsize(760, 480)

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=8, pady=8)

        # Вкладка: Гіпотези (вільний текст)
        self.tab_hypothesis = ttk.Frame(notebook)
        notebook.add(self.tab_hypothesis, text="Гіпотеза (текст)")

        self.hypothesis_label = ttk.Label(
            self.tab_hypothesis,
            text=(
                "Введіть гіпотезу українською (напр.:  троянда є дводольні / "
                "насінина частина плід / пшениця росте в степ):"
            ),
        )
        self.hypothesis_label.pack(anchor="w", padx=8, pady=(8, 4))

        self.hypothesis_entry = ttk.Entry(self.tab_hypothesis)
        self.hypothesis_entry.pack(fill="x", padx=8, pady=4)
        self.hypothesis_entry.bind("<Return>", lambda e: self.on_check_hypothesis())

        self.hypothesis_button = ttk.Button(
            self.tab_hypothesis, text="Перевірити", command=self.on_check_hypothesis
        )
        self.hypothesis_button.pack(anchor="w", padx=8, pady=(4, 8))

        self.hypothesis_output = tk.Text(self.tab_hypothesis, height=18, wrap="word")
        self.hypothesis_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Вкладка: Ручна перевірка відношень
        self.tab_relations = ttk.Frame(notebook)
        notebook.add(self.tab_relations, text="Відношення (ручна перевірка)")

        form = ttk.Frame(self.tab_relations)
        form.pack(fill="x", padx=8, pady=8)

        ttk.Label(form, text="A:").grid(row=0, column=0, sticky="w")
        self.input_a = ttk.Entry(form, width=30)
        self.input_a.grid(row=0, column=1, padx=4, pady=2)

        ttk.Label(form, text="B:").grid(row=0, column=2, sticky="w")
        self.input_b = ttk.Entry(form, width=30)
        self.input_b.grid(row=0, column=3, padx=4, pady=2)

        self.btn_explain = ttk.Button(form, text="Пояснити (будь-який зв’язок)", command=self.on_explain)
        self.btn_explain.grid(row=0, column=4, padx=6)

        self.btn_check_isa = ttk.Button(form, text="Перевірити is_a(A,B)", command=self.on_check_isa)
        self.btn_check_isa.grid(row=1, column=1, sticky="ew", padx=4, pady=4)

        self.btn_check_partof = ttk.Button(form, text="A є частиною B", command=self.on_check_partof)
        self.btn_check_partof.grid(row=1, column=2, sticky="ew", padx=4, pady=4)

        self.btn_check_haspart = ttk.Button(form, text="A має частину B", command=self.on_check_haspart)
        self.btn_check_haspart.grid(row=1, column=3, sticky="ew", padx=4, pady=4)

        self.btn_check_growsin = ttk.Button(form, text="A росте в/у B", command=self.on_check_growsin)
        self.btn_check_growsin.grid(row=1, column=4, sticky="ew", padx=6, pady=4)

        self.relations_output = tk.Text(self.tab_relations, height=18, wrap="word")
        self.relations_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        # Вкладка: Перевірка вимог
        self.tab_requirements = ttk.Frame(notebook)
        notebook.add(self.tab_requirements, text="Перевірка вимог")

        self.btn_requirements = ttk.Button(
            self.tab_requirements, text="Перевірити вимоги", command=self.on_requirements
        )
        self.btn_requirements.pack(anchor="w", padx=8, pady=8)

        self.requirements_output = tk.Text(self.tab_requirements, height=18, wrap="word")
        self.requirements_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    #  Обробники подій GUI
    def on_check_hypothesis(self) -> None:
        text = self.hypothesis_entry.get().strip()
        if not text:
            messagebox.showinfo("Підказка", "Введіть гіпотезу, напр.:  троянда є дводольні")
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
        a = normalize_id(self.input_a.get())
        b = normalize_id(self.input_b.get())
        a_class = INSTANCES.get(a, a)  # якщо A — інстанс, беремо його клас
        ok = (a == b) or is_subclass_of(a, b) or is_subclass_of(a_class, b)
        msg = f'Гіпотеза: "{a} є {b}" → ' + ("Істина\n\n" + explain_relationship(a, b) if ok else "Хиба")
        self.relations_output.delete("1.0", "end")
        self.relations_output.insert("1.0", msg)

    def on_check_partof(self) -> None:
        a = self.input_a.get()
        b = self.input_b.get()
        ok = is_part_of_transitive(a, b)
        msg = f'Гіпотеза: "{a} є частиною {b}" → ' + ("Істина\n\n" + explain_relationship(a, b) if ok else "Хиба")
        self.relations_output.delete("1.0", "end")
        self.relations_output.insert("1.0", msg)

    def on_check_haspart(self) -> None:
        a = self.input_a.get()
        b = self.input_b.get()
        ok = has_part_transitive(a, b)
        msg = f'Гіпотеза: "{a} має частину {b}" → ' + ("Істина\n\n" + explain_relationship(a, b) if ok else "Хиба")
        self.relations_output.delete("1.0", "end")
        self.relations_output.insert("1.0", msg)

    def on_check_growsin(self) -> None:
        a = self.input_a.get()
        b = self.input_b.get()
        ok = is_grows_in_direct(a, b)
        msg = f'Гіпотеза: "{a} росте в {b}" → ' + ("Істина\n\n" + explain_relationship(a, b) if ok else "Хиба")
        self.relations_output.delete("1.0", "end")
        self.relations_output.insert("1.0", msg)

    def on_requirements(self) -> None:
        self.requirements_output.delete("1.0", "end")
        self.requirements_output.insert("1.0", get_requirements_report())


# 8) Точка входу
if __name__ == "__main__":
    OntologyApp().mainloop()



