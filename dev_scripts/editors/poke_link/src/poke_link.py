import tkinter as tk
from tkinter import ttk, filedialog
from PIL import Image, ImageTk
import json, os, shutil

class PokedexApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Pokédex Manager")
        self.geometry("700x720")
        self.minsize(700, 720)
        self.configure(bg='#f6f8fa')
        style = ttk.Style(self)
        style.theme_use('clam')
        style.configure('.', font=('Segoe UI', 13))
        style.configure('Card.TFrame', background='#fff', borderwidth=1, relief='raised')
        style.configure('TLabel', background='#f6f8fa')
        style.configure('Header.TLabel', font=('Segoe UI', 18, 'bold'), background='#f6f8fa')
        style.configure('Section.TLabel', font=('Segoe UI', 12, 'bold'), background='#f6f8fa', foreground='#444')
        style.configure('Error.TLabel', foreground='red', background='#f6f8fa')

        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(self.script_dir, "..", "data")
        self.sprites_dir = os.path.join(self.script_dir, "..", "sprites")
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.sprites_dir, exist_ok=True)
        self.json_path = os.path.join(self.data_dir, "pokemon.json")
        if not os.path.exists(self.json_path):
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump([], f)
        self.pokemon_data = []
        self.load_data()
        self.image_cache = {}

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.create_input_tab()
        self.create_view_tab()

    def load_data(self):
        try:
            with open(self.json_path, "r", encoding="utf-8") as f:
                self.pokemon_data = json.load(f)
        except Exception:
            self.pokemon_data = []

    def save_data(self):
        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(self.pokemon_data, f, indent=4)

    def create_input_tab(self):
        TYPES = [
            "None", "Normal", "Fire", "Water", "Grass", "Electric", "Ice", "Fighting",
            "Poison", "Ground", "Flying", "Psychic", "Bug", "Rock", "Ghost", "Dragon",
            "Dark", "Steel", "Fairy"
        ]
        tab = ttk.Frame(self.notebook, padding=4)
        self.notebook.add(tab, text="Input Pokémon")

        card = ttk.Frame(tab, style='Card.TFrame', padding=10)
        card.pack(padx=8, pady=8, anchor=tk.N, fill=tk.BOTH, expand=False)

        self.input_errors = {}
        row = 0
        ttk.Label(card, text="Add Pokémon", style='Header.TLabel').grid(row=row, column=0, columnspan=2, pady=(0, 10), sticky='w')

        # Name
        row += 1
        ttk.Label(card, text="Name", style='Section.TLabel').grid(row=row, column=0, sticky='w')
        self.name_entry = ttk.Entry(card, width=22)
        self.name_entry.grid(row=row, column=1, sticky='ew')
        self.input_errors['name'] = ttk.Label(card, style='Error.TLabel')
        self.input_errors['name'].grid(row=row+1, column=0, columnspan=2, sticky='w')

        # Type
        row += 2
        ttk.Label(card, text="Primary Type", style='Section.TLabel').grid(row=row, column=0, sticky='w')
        self.primary_type = ttk.Combobox(card, values=TYPES, state="readonly", width=12)
        self.primary_type.set("Normal")
        self.primary_type.grid(row=row, column=1, sticky='ew')

        row += 1
        ttk.Label(card, text="Secondary Type", style='Section.TLabel').grid(row=row, column=0, sticky='w')
        self.secondary_type = ttk.Combobox(card, values=TYPES, state="readonly", width=12)
        self.secondary_type.set("None")
        self.secondary_type.grid(row=row, column=1, sticky='ew')

        # Abilities
        row += 1
        ttk.Label(card, text="Abilities (max 3)", style='Section.TLabel').grid(row=row, column=0, sticky='w')
        self.abilities_entry = ttk.Entry(card, width=22)
        self.abilities_entry.grid(row=row, column=1, sticky='ew')
        self.abilities_entry.insert(0, "Overgrow, Chlorophyll")
        self.input_errors['abilities'] = ttk.Label(card, style='Error.TLabel')
        self.input_errors['abilities'].grid(row=row+1, column=0, columnspan=2, sticky='w')

        # Base Stats in two columns of 3
        row += 2
        ttk.Label(card, text="Base Stats", style='Section.TLabel').grid(row=row, column=0, columnspan=2, sticky='w')
        stats_frame = ttk.Frame(card)
        stats_frame.grid(row=row+1, column=0, columnspan=2, sticky='w', pady=2)
        stats = ["HP", "Attack", "Defense", "Sp. Atk", "Sp. Def", "Speed"]
        self.stat_entries = {}
        for i, stat in enumerate(stats):
            r = i % 3
            c = i // 3
            lbl = ttk.Label(stats_frame, text=f"{stat}:")
            lbl.grid(row=r, column=c*2, padx=1, sticky='e')
            ent = ttk.Entry(stats_frame, width=5)
            ent.insert(0, "50")
            ent.grid(row=r, column=c*2+1, padx=2, sticky='w')
            ent.bind('<KeyRelease>', self.update_total_stats)
            self.stat_entries[stat] = ent
        self.total_label = ttk.Label(card, text="Total: 300", font=('Segoe UI', 11, 'bold'), foreground='#0a7e07')
        self.total_label.grid(row=row+2, column=0, columnspan=2, sticky='w')
        self.input_errors['stats'] = ttk.Label(card, style='Error.TLabel')
        self.input_errors['stats'].grid(row=row+3, column=0, columnspan=2, sticky='w')

        # Evolution
        row += 4
        ttk.Label(card, text="Evolution (comma-separated)", style='Section.TLabel').grid(row=row, column=0, sticky='w')
        self.evo_entry = ttk.Entry(card, width=22)
        self.evo_entry.insert(0, "")
        self.evo_entry.grid(row=row, column=1, sticky='ew')
        self.input_errors['evo'] = ttk.Label(card, style='Error.TLabel')
        self.input_errors['evo'].grid(row=row+1, column=0, columnspan=2, sticky='w')

        # Sprites: Front and Back
        row += 2
        ttk.Label(card, text="Front Sprite", style='Section.TLabel').grid(row=row, column=0, sticky='w')
        front_btn = ttk.Button(card, text="Select…", command=self.select_front_sprite)
        front_btn.grid(row=row, column=1, sticky='w')
        self.front_sprite_label = ttk.Label(card, text="No file", background="#fff", font=('Segoe UI', 11, 'italic'))
        self.front_sprite_label.grid(row=row+1, column=0, columnspan=2, sticky='w')

        ttk.Label(card, text="Back Sprite", style='Section.TLabel').grid(row=row+2, column=0, sticky='w')
        back_btn = ttk.Button(card, text="Select…", command=self.select_back_sprite)
        back_btn.grid(row=row+2, column=1, sticky='w')
        self.back_sprite_label = ttk.Label(card, text="No file", background="#fff", font=('Segoe UI', 11, 'italic'))
        self.back_sprite_label.grid(row=row+3, column=0, columnspan=2, sticky='w')

        self.input_errors['sprites'] = ttk.Label(card, style='Error.TLabel')
        self.input_errors['sprites'].grid(row=row+4, column=0, columnspan=2, sticky='w')
        self.front_sprite_path = None
        self.back_sprite_path = None

        # Add Button
        row += 5
        add_btn = ttk.Button(card, text="➕ Add Pokémon", command=self.add_pokemon)
        add_btn.grid(row=row, column=0, columnspan=2, pady=(8,0), sticky='w')

    def update_total_stats(self, event=None):
        total = 0
        for ent in self.stat_entries.values():
            val = ent.get().strip()
            if val.isdigit():
                total += int(val)
        color = '#0a7e07' if total >= 300 else '#c11'
        self.total_label.config(text=f"Total: {total}", foreground=color)

    def select_front_sprite(self):
        path = filedialog.askopenfilename(
            title="Select Front Sprite",
            filetypes=[("PNG Images", "*.png")],
            initialdir=self.sprites_dir
        )
        if path:
            self.front_sprite_path = path
            self.front_sprite_label.config(text=os.path.basename(path))

    def select_back_sprite(self):
        path = filedialog.askopenfilename(
            title="Select Back Sprite",
            filetypes=[("PNG Images", "*.png")],
            initialdir=self.sprites_dir
        )
        if path:
            self.back_sprite_path = path
            self.back_sprite_label.config(text=os.path.basename(path))

    def add_pokemon(self):
        for e in self.input_errors.values():
            e.config(text='')
        has_err = False

        name = self.name_entry.get().strip()
        types = [t for t in [self.primary_type.get(), self.secondary_type.get()] if t and t != "None"]
        abilities = [a.strip() for a in self.abilities_entry.get().split(',') if a.strip()]
        evolutions = [e.strip() for e in self.evo_entry.get().split(',') if e.strip()]

        # Required evolution entry check
        if not evolutions:
            self.input_errors['evo'].config(
                text="At least one evolution is required. Use the Pokémon's name if it has no evolutions."
            )
            has_err = True

        if not name:
            self.input_errors['name'].config(text="Please enter a Pokémon name.")
            has_err = True
        if not types:
            self.input_errors['name'].config(text="Select at least one type.")
            has_err = True
        if len(abilities) > 3:
            self.input_errors['abilities'].config(text="Only up to 3 abilities.")
            has_err = True
        for stat, ent in self.stat_entries.items():
            val = ent.get().strip()
            if not val.isdigit():
                self.input_errors['stats'].config(text=f"{stat} must be numeric.")
                has_err = True
                break

        if has_err:
            return

        # If only one evolution, set it to the Pokémon's name
        if len(evolutions) == 0:
            evolutions = [name]
        elif len(evolutions) == 1 and not evolutions[0]:
            evolutions[0] = name

        # If a sprite is not selected, use placeholder.png
        PLACEHOLDER = "placeholder.png"
        name_slug = name.lower().replace(' ', '_')
        front_filename = f"{name_slug}_front.png" if self.front_sprite_path else PLACEHOLDER
        back_filename = f"{name_slug}_back.png" if self.back_sprite_path else PLACEHOLDER
        if self.front_sprite_path:
            shutil.copy(self.front_sprite_path, os.path.join(self.sprites_dir, front_filename))
        if self.back_sprite_path:
            shutil.copy(self.back_sprite_path, os.path.join(self.sprites_dir, back_filename))

        stats_data = {stat: int(self.stat_entries[stat].get().strip()) for stat in self.stat_entries}
        entry = {
            "name": name,
            "types": types,
            "abilities": abilities,
            "stats": stats_data,
            "evolutions": evolutions,
            "front_sprite": front_filename,
            "back_sprite": back_filename
        }
        self.pokemon_data.append(entry)
        self.save_data()

        self.name_entry.delete(0, tk.END)
        self.abilities_entry.delete(0, tk.END)
        self.evo_entry.delete(0, tk.END)
        for ent in self.stat_entries.values():
            ent.delete(0, tk.END)
            ent.insert(0, "50")
        self.front_sprite_path = None
        self.back_sprite_path = None
        self.front_sprite_label.config(text="No file")
        self.back_sprite_label.config(text="No file")
        self.update_total_stats()
        self.populate_families()

    # ---- VIEW TAB ----
    def create_view_tab(self):
        tab = ttk.Frame(self.notebook, padding=0)
        self.notebook.add(tab, text="Pokédex")

        left = ttk.Frame(tab, width=200, padding=(8,0,6,6), style='Card.TFrame')
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(5,0), pady=8)
        right = ttk.Frame(tab, padding=(8,10,10,10), style='Card.TFrame')
        right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=0, pady=8)

        ttk.Label(left, text="Pokédex List", style='Header.TLabel').pack(pady=(2,12))

        self.families_listbox = tk.Listbox(left, font=('Segoe UI', 12), bg="#f7faff", activestyle='none', width=29, height=32)
        self.families_listbox.pack(fill=tk.Y, expand=True, padx=(2,2), pady=(0,8))
        self.families_listbox.bind('<<ListboxSelect>>', self.on_family_select)
        self.families_listbox.bind('<Up>', self.on_up_down)
        self.families_listbox.bind('<Down>', self.on_up_down)
        self.families_listbox.focus_set()

        self.evo_sprite_frame = ttk.Frame(right)
        self.evo_sprite_frame.pack(anchor='w', pady=(4,12))

        self.info_card = ttk.Frame(right, style='Card.TFrame', padding=14)
        self.info_card.pack(fill=tk.BOTH, expand=True)
        self.info_label = ttk.Label(self.info_card, font=('Segoe UI', 13), justify=tk.LEFT, background="#fff")
        self.info_label.pack(anchor=tk.NW, pady=(0,0))

        self.selected_family_idx = None
        self.selected_poke_idx = 0
        self.evolution_families = []
        self.populate_families()

        self.bind_all('<Left>', self.on_left_right)
        self.bind_all('<Right>', self.on_left_right)

    def group_by_evolution(self):
        families = {}
        for p in self.pokemon_data:
            evo_tuple = tuple([e.lower() for e in p.get('evolutions', [])])
            if evo_tuple and evo_tuple not in families:
                family = [x for x in self.pokemon_data if tuple([e.lower() for e in x.get('evolutions', [])]) == evo_tuple]
                def evo_index(x):
                    try: return evo_tuple.index(x['name'].lower())
                    except: return 0
                family.sort(key=evo_index)
                families[evo_tuple] = family
        return list(sorted(families.values(), key=lambda fam: fam[0]['name'].lower() if fam else ""))

    def populate_families(self):
        self.evolution_families = self.group_by_evolution()
        self.families_listbox.delete(0, tk.END)
        for fam in self.evolution_families:
            label = ' → '.join([pk['name'] for pk in fam])
            self.families_listbox.insert(tk.END, label)
        self.clear_info()
        self.selected_family_idx = 0
        self.selected_poke_idx = 0

    def clear_info(self):
        for widget in self.evo_sprite_frame.winfo_children():
            widget.destroy()
        self.info_label.config(text="")
        for widget in self.info_card.winfo_children():
            if widget != self.info_label:
                widget.destroy()

    def on_family_select(self, event=None):
        sel = self.families_listbox.curselection()
        if not sel:
            self.clear_info()
            return
        idx = sel[0]
        self.selected_family_idx = idx
        self.selected_poke_idx = 0  # Default to FIRST evolution!
        self.show_pokemon_family(self.evolution_families[idx], highlight_idx=0)

    def show_pokemon_family(self, family, highlight_idx=0):
        for widget in self.evo_sprite_frame.winfo_children():
            widget.destroy()
        for i, poke in enumerate(family):
            is_selected = i == highlight_idx
            sprite_path = poke['front_sprite'] if not getattr(self, 'sprite_toggle', {}).get(poke['name'], False) else poke['back_sprite']
            img = self.load_sprite(sprite_path)
            lbl = ttk.Label(
                self.evo_sprite_frame,
                image=img,
                borderwidth=3,
                relief='solid' if is_selected else 'flat',
                background='#d4ffd6' if is_selected else "#f6f8fa",
                cursor='hand2'
            )
            lbl.image = img
            lbl.grid(row=0, column=i*2, padx=2)
            lbl.bind("<Button-1>", lambda e, idx=i: self.on_sprite_click(idx))
            lbl.bind("<Button-3>", lambda e, pk=poke['name']: self.toggle_sprite(pk))
            if i < len(family)-1:
                arr = ttk.Label(self.evo_sprite_frame, text="→", font=('Segoe UI', 16, 'bold'), background='#f6f8fa')
                arr.grid(row=0, column=i*2+1)

        self.selected_poke_idx = highlight_idx
        selected = family[highlight_idx]
        for widget in self.info_card.winfo_children():
            if widget != self.info_label:
                widget.destroy()
        total = sum(selected['stats'].values())
        info_lines = [
            f"Name: {selected['name']}",
            f"Type(s): {', '.join(selected['types'])}",
            f"Abilities: {', '.join(selected.get('abilities', [])) or 'None'}",
            "Base Stats:"
        ]
        for k, v in selected['stats'].items():
            info_lines.append(f"   {k}: {v}")
        info_lines.append("")
        info_lines.append(f"Base Stat Total: {total}")
        self.info_label.config(text="\n".join(info_lines), font=('Segoe UI', 13, ''))

    def toggle_sprite(self, poke_name):
        if not hasattr(self, 'sprite_toggle'):
            self.sprite_toggle = {}
        self.sprite_toggle[poke_name] = not self.sprite_toggle.get(poke_name, False)
        if self.selected_family_idx is not None:
            family = self.evolution_families[self.selected_family_idx]
            self.show_pokemon_family(family, highlight_idx=self.selected_poke_idx)

    def on_sprite_click(self, idx):
        if self.selected_family_idx is not None:
            family = self.evolution_families[self.selected_family_idx]
            self.show_pokemon_family(family, highlight_idx=idx)

    def on_left_right(self, event):
        if self.selected_family_idx is None or not self.evolution_families:
            return
        family = self.evolution_families[self.selected_family_idx]
        if event.keysym == 'Left':
            idx = (self.selected_poke_idx - 1) % len(family)
        elif event.keysym == 'Right':
            idx = (self.selected_poke_idx + 1) % len(family)
        else:
            return
        self.show_pokemon_family(family, highlight_idx=idx)

    def on_up_down(self, event):
        n = len(self.evolution_families)
        if n == 0: return
        idx = self.selected_family_idx or 0
        if event.keysym == 'Up':
            idx = (idx - 1) % n
        elif event.keysym == 'Down':
            idx = (idx + 1) % n
        self.families_listbox.selection_clear(0, tk.END)
        self.families_listbox.selection_set(idx)
        self.families_listbox.event_generate('<<ListboxSelect>>')

    def load_sprite(self, filename, size=(90,90)):
        if not filename: return None
        path = os.path.join(self.sprites_dir, filename)
        cache_key = (path, size)
        if cache_key in self.image_cache:
            return self.image_cache[cache_key]
        if not os.path.exists(path): return None
        try:
            img = Image.open(path).convert("RGBA")
            img = img.resize(size, resample=Image.NEAREST)
            photo = ImageTk.PhotoImage(img)
            self.image_cache[cache_key] = photo
            return photo
        except Exception:
            return None

if __name__ == '__main__':
    app = PokedexApp()
    app.mainloop()
