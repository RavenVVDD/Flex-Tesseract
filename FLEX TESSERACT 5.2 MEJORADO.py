# ==============================
# FLEX TESSERACT 5.4 — Persistencia visual por día + Detallado agrupado (tipo Presis)
# ==============================
# Requisitos:
#   pip install pillow pytesseract pandas ttkbootstrap (opcional)
#   (Para exportación Markdown: pip install tabulate)
#
# Cambios clave vs 5.3:
# - Persistencia detallada REAL por etiqueta (siempre) con: Cordon, Ciudad, Subregión, Src, Manual, ts.
# - Migración automática de subregiones.json viejo al nuevo esquema.
# - Confirmaciones manuales con precio correcto (usa el cordón elegido).
# - Exportación detallada (Excel/Markdown) AGRUPADA por (Fecha, Día, Cordón, Localidad, Domicilio), con Cantidad e Importe.
# - Reset por día (selector Lunes–Viernes) además del reset semanal.
# - NUEVO: “Paquetes Día” (total por día de fotos/paquetes) y “Total semanal de paquetes” en el pie.
# - Limpieza de código y comentarios.

import os
import json
import zipfile
from datetime import datetime
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
import pytesseract
import pandas as pd

# === OCR (ajustar a tu path de instalación en Windows si fuera distinto) ===
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# === UI Moderna opcional ===
try:
    import ttkbootstrap as ttkb
    from ttkbootstrap.constants import *
    BOOTSTRAP = True
except Exception:
    BOOTSTRAP = False

# === Datos base ===
CORDONES = {
    "Primer cordón": [
        "AVELLANEDA", "HURLINGHAM", "ITUZAINGO", "LA MATANZA NORTE", "LANUS",
        "LOMAS DE ZAMORA", "MORON", "SAN FERNANDO", "SAN ISIDRO", "SAN MARTIN",
        "TRES DE FEBRERO", "VICENTE LOPEZ"
    ],
    "Segundo cordón": [
        "ALMIRANTE BROWN", "BERAZATEGUI", "ESTEBAN ECHEVERRIA", "EZEIZA",
        "FLORENCIO VARELA", "JOSE C PAZ", "LA MATANZA SUR", "MALVINAS ARGENTINAS",
        "MERLO", "MORENO", "QUILMES", "SAN MIGUEL", "TIGRE"
    ],
    "Tercer cordón (CABA)": ["CABA"],
    "Cuarto cordón": [
        "BERISSO", "CAMPANA", "CAÑUELAS", "DEL VISO", "DERQUI", "ENSENADA",
        "ESCOBAR", "GARIN", "GENERAL RODRIGUEZ", "GUERNICA", "INGENIERO MASCHWITZ",
        "LA PLATA CENTRO", "LA PLATA NORTE", "LA PLATA OESTE", "LUJAN",
        "MARCOS PAZ", "NORDELTA", "PILAR", "SAN VICENTE", "VILLA ROSA", "ZARATE"
    ]
}
PRECIOS = {
    "Primer cordón": 5538,
    "Segundo cordón": 7638,
    "Tercer cordón (CABA)": 3457,
    "Cuarto cordón": 9650,
}

# === Archivos persistentes ===
DATA_FILE = "data_semanal.json"    # { "Lunes": { "Primer cordón": n, ... }, ... }
SUBREG_FILE = "subregiones.json"   # { "Lunes": [ {Cordon, Ciudad, Subregión, Src, Manual, ts}, ... ], ... }
PEND_FILE = "pendientes.json"      # [ "path/img1.jpg", ... ]


# === JSON utils ===
def load_json(path: str, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return default


def save_json(path: str, data) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# === OCR utils ===
def identificar_cordon_por_ciudad(texto: str):
    """
    Busca en el texto OCR una ciudad y, si la encuentra, devuelve (cordón, ciudad, subregión).
    La subregión se toma como la línea siguiente a la ciudad, si existe.
    """
    lineas = texto.splitlines()
    for i, linea in enumerate(lineas):
        uline = linea.upper().strip()
        for cordon, ciudades in CORDONES.items():
            for ciudad in ciudades:
                if ciudad in uline:
                    subregion = lineas[i + 1].strip() if i + 1 < len(lineas) else ""
                    return cordon, ciudad, subregion
    return "cordon_no_identificado", None, None


def ocr_con_rotaciones(img) -> str:
    """
    Ejecuta OCR con rotaciones 0/90/180/270 y devuelve el primer resultado no vacío.
    """
    for ang in (0, 90, 180, 270):
        txt = pytesseract.image_to_string(img.rotate(ang, expand=True), lang="eng")
        if txt.strip():
            return txt
    return ""


# === App principal ===
class ClasificadorApp(tk.Tk):
    def __init__(self):
        super().__init__()
        if BOOTSTRAP:
            self.style = ttkb.Style(theme="darkly")

        self.title("FLEX TESSERACT 5.4 — Persistencia Visual y Detallado Agrupado")
        self.geometry("1360x800")
        self.minsize(1100, 720)

        # Carpeta fija para ZIPs procesados
        self.tmpdir = os.path.join(os.getcwd(), "procesos_tmp")
        os.makedirs(self.tmpdir, exist_ok=True)

        # Estado persistente base
        self.dias = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes"]
        self.dia = tk.StringVar(value="Lunes")
        self.data = load_json(DATA_FILE, {d: {} for d in self.dias})
        self.subregs = load_json(SUBREG_FILE, {d: [] for d in self.dias})
        self.pendientes = load_json(PEND_FILE, [])
        self._img_refs_pend = []

        # Selector para "Resetear día"
        self.reset_dia_var = tk.StringVar(value=self.dia.get())  # default = día actual

        # Mantener sincronizado el combo de reset con el selector principal de día
        try:
            self.dia.trace_add("write", lambda *_: self.reset_dia_var.set(self.dia.get()))
        except Exception:
            # Compatibilidad Python <3.8
            self.dia.trace("w", lambda *_: self.reset_dia_var.set(self.dia.get()))

        # Migración de esquema (compatibilidad hacia 5.4)
        self._migrate_subregs_schema()

        # Construcción UI + renders iniciales
        self._build_ui()
        self._render_tabla()
        self._render_pendientes()
        self._update_pend_count()

    # ---------------- UI ----------------
    def _build_ui(self) -> None:
        # Sidebar
        self.sidebar = ttk.Frame(self, padding=12)
        self.sidebar.pack(side="left", fill="y")

        ttk.Label(self.sidebar, text="Panel de Control", font=("Segoe UI", 14, "bold")).pack(pady=(0, 12))
        ttk.Label(self.sidebar, text="Día de trabajo").pack(anchor="w")

        ttk.Combobox(self.sidebar, textvariable=self.dia, values=self.dias, state="readonly").pack(fill="x", pady=6)

        ttk.Button(self.sidebar, text="📸 Cargar imágenes", command=self.cargar_imgs).pack(fill="x", pady=4)
        ttk.Button(self.sidebar, text="🗜️ Cargar .ZIP", command=self.cargar_zip).pack(fill="x", pady=4)

        ttk.Separator(self.sidebar).pack(fill="x", pady=8)

        ttk.Button(self.sidebar, text="🧮 Exportar Excel (resumen)", command=self.export_excel).pack(fill="x", pady=4)
        ttk.Button(self.sidebar, text="📦 Exportar Detallado XLS (agrupado)", command=self.export_detallado_excel).pack(fill="x", pady=4)
        ttk.Button(self.sidebar, text="📝 Exportar Detallado MD (agrupado)", command=self.export_detallado_markdown).pack(fill="x", pady=4)

        ttk.Button(self.sidebar, text="♻️ Reset Semana", command=self.reset_sem).pack(fill="x", pady=4)

        ttk.Separator(self.sidebar).pack(fill="x", pady=6)

        # --- Reset por día (combo + botón) ---
        row_reset_dia = ttk.Frame(self.sidebar)
        row_reset_dia.pack(fill="x", pady=4)

        ttk.Label(row_reset_dia, text="🧹 Resetear día:").pack(side="left")

        cb_reset = ttk.Combobox(
            row_reset_dia,
            textvariable=self.reset_dia_var,
            values=self.dias,
            state="readonly",
            width=14
        )
        cb_reset.pack(side="left", padx=6)

        ttk.Button(
            row_reset_dia,
            text="Reset",
            command=self.reset_dia
        ).pack(side="left")

        ttk.Separator(self.sidebar).pack(fill="x", pady=8)

        self.progress = ttk.Progressbar(self.sidebar, length=200)
        self.progress.pack(pady=(4, 8))

        self.lbl_pend = ttk.Label(self.sidebar, text="Pendientes: 0", font=("Segoe UI", 10, "bold"))
        self.lbl_pend.pack(anchor="w")

        # Panel principal scrollable
        self.canvas = tk.Canvas(self, highlightthickness=0, bg="#222")
        vsb = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=vsb.set)

        vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.main_frame = ttk.Frame(self.canvas, padding=10)
        self.canvas.create_window((0, 0), window=self.main_frame, anchor="nw")
        self.main_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))

        self.tbl_frame = ttk.Frame(self.main_frame)
        self.tbl_frame.pack(fill="x", pady=(0, 12))

        self.pend_frame = ttk.Frame(self.main_frame)
        self.pend_frame.pack(fill="x")

    # ---------------- Carga/Procesamiento ----------------
    def cargar_imgs(self) -> None:
        files = filedialog.askopenfilenames(filetypes=[("Imágenes", "*.jpg;*.jpeg;*.png")])
        if files:
            self._procesar(files)

    def cargar_zip(self) -> None:
        path = filedialog.askopenfilename(filetypes=[("ZIP files", "*.zip")])
        if not path:
            return

        out = os.path.join(self.tmpdir, datetime.now().strftime("%Y%m%d_%H%M%S"))
        os.makedirs(out, exist_ok=True)

        with zipfile.ZipFile(path, "r") as z:
            z.extractall(out)

        imgs = [
            os.path.join(r, f)
            for r, _, fs in os.walk(out)
            for f in fs
            if f.lower().endswith((".jpg", ".jpeg", ".png"))
        ]

        if not imgs:
            messagebox.showwarning("ZIP vacío", "No se encontraron imágenes dentro del ZIP.")
            return

        self._procesar(imgs)

    def _procesar(self, paths) -> None:
        dia = self.dia.get()
        self.progress.configure(maximum=len(paths), value=0)

        for i, p in enumerate(paths, 1):
            try:
                img = Image.open(p)
                txt = ocr_con_rotaciones(img)
                cordon, ciudad, sub = identificar_cordon_por_ciudad(txt)

                if cordon == "cordon_no_identificado":
                    if p not in self.pendientes:
                        self.pendientes.append(p)
                else:
                    # Contador por día/cordón
                    self.data[dia][cordon] = self.data[dia].get(cordon, 0) + 1
                    # Fila detallada SIEMPRE (aunque subregión esté vacía)
                    self._append_detalle(
                        dia=dia,
                        cordon=cordon,
                        ciudad=ciudad or "",
                        subregion=sub or "",
                        src_path=p,
                        manual=False,
                    )

            except Exception as e:
                print("Error procesando:", p, e)

            self.progress.configure(value=i)
            self.update_idletasks()

        # Guardar persistencia
        save_json(DATA_FILE, self.data)
        save_json(SUBREG_FILE, self.subregs)
        save_json(PEND_FILE, self.pendientes)

        self._render_tabla()
        self._render_pendientes()
        self._update_pend_count()

    # ---------------- Pendientes ----------------
    def _render_pendientes(self) -> None:
        for w in self.pend_frame.winfo_children():
            w.destroy()
        self._img_refs_pend.clear()

        ttk.Label(
            self.pend_frame,
            text="Pendientes de revisión manual",
            font=("Segoe UI", 12, "bold")
        ).pack(anchor="w", pady=(0, 8))

        if not self.pendientes:
            ttk.Label(self.pend_frame, text="🎉 No hay imágenes pendientes.").pack(anchor="w", pady=5)
            return

        dia_actual = self.dia.get()

        for path in list(self.pendientes):
            if not os.path.exists(path):
                # Si el archivo ya no existe, lo omitimos
                continue

            try:
                img = Image.open(path)
                img.thumbnail((120, 120))
                tk_img = ImageTk.PhotoImage(img)
                self._img_refs_pend.append(tk_img)

                cont = ttk.Frame(self.pend_frame, padding=6)
                cont.pack(fill="x", pady=6)

                # Miniatura clickeable
                lbl_img = tk.Label(cont, image=tk_img, cursor="hand2")
                lbl_img.pack(side="left")
                if hasattr(os, "startfile"):
                    lbl_img.bind("<Button-1>", lambda e, p=path: os.startfile(p))

                info = ttk.Frame(cont)
                info.pack(side="left", padx=10, fill="x", expand=True)

                ttk.Label(info, text=os.path.basename(path)).pack(anchor="w")

                row2 = ttk.Frame(info)
                row2.pack(anchor="w", pady=(4, 0))

                cb = ttk.Combobox(row2, values=list(CORDONES.keys()), width=24, state="readonly")
                cb.set("Seleccionar cordón")
                cb.pack(side="left", padx=(0, 5))

                entry = ttk.Entry(row2, width=35)
                entry.insert(0, "Subregión (domicilio) opcional")
                entry.pack(side="left", padx=(0, 5))

                def confirmar(cbox=cb, ebox=entry, ruta=path, container=cont):
                    cordon_sel = cbox.get()
                    subr = ebox.get().strip()

                    if cordon_sel not in CORDONES:
                        messagebox.showwarning("Atención", "Seleccioná un cordón válido.")
                        return

                    # Sumar contador
                    self.data[dia_actual][cordon_sel] = self.data[dia_actual].get(cordon_sel, 0) + 1

                    # Guardar detalle con el cordón elegido; ciudad vacía si no la sabemos.
                    self._append_detalle(
                        dia=dia_actual,
                        cordon=cordon_sel,
                        ciudad="",
                        subregion=(subr if subr and "opcional" not in subr.lower() else ""),
                        src_path=ruta,
                        manual=True,
                    )

                    # Limpiar pendiente
                    if ruta in self.pendientes:
                        self.pendientes.remove(ruta)

                    container.destroy()
                    save_json(DATA_FILE, self.data)
                    save_json(SUBREG_FILE, self.subregs)
                    save_json(PEND_FILE, self.pendientes)
                    self._render_tabla()
                    self._update_pend_count()

                ttk.Button(row2, text="Confirmar", command=confirmar).pack(side="left")

            except Exception as e:
                print("Error mostrando pendiente:", e)

    # ---------------- Tabla resumen (conteo por día/cordón) ----------------
    def _render_tabla(self) -> None:
        for w in self.tbl_frame.winfo_children():
            w.destroy()

        # Columnas: Día, cordones (conteos), Paquetes Día (total de conteos), Total $ Día
        headers = ["Día"] + list(PRECIOS.keys()) + ["Paquetes Día", "Total $ Día"]
        table = ttk.Treeview(self.tbl_frame, columns=headers, show="headings", height=6)

        for h in headers:
            table.heading(h, text=h)
            # un poco más angosto para cordones y más ancho para totales
            width = 120 if h in PRECIOS else (140 if h == "Día" else 140)
            table.column(h, width=width, anchor="center")

        table.pack(fill="x")

        total_sem_pesos = 0
        total_sem_paquetes = 0

        for dia, vals in self.data.items():
            paquetes_dia = sum(vals.values())
            total_dia_pesos = sum(PRECIOS.get(c, 0) * n for c, n in vals.items())

            total_sem_paquetes += paquetes_dia
            total_sem_pesos += total_dia_pesos

            row = [dia] + [vals.get(c, 0) for c in PRECIOS] + [paquetes_dia, f"${total_dia_pesos:,}"]
            table.insert("", "end", values=row)

        # Pie con totales semanales (lado a lado)
        footer = ttk.Frame(self.tbl_frame)
        footer.pack(fill="x", pady=(6, 0))

        ttk.Label(
            footer,
            text=f"💰 Total semanal ($): ${total_sem_pesos:,}",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=(0, 12))

        ttk.Label(
            footer,
            text=f"📦 Total semanal de paquetes: {total_sem_paquetes:,}",
            font=("Segoe UI", 11, "bold")
        ).pack(side="left")

    # ---------------- Exportar (resumen por día) ----------------
    def export_excel(self) -> None:
        # Estructurar DataFrame con conteos por cordón
        df = pd.DataFrame.from_dict(self.data, orient="index")
        for c in PRECIOS:
            if c not in df:
                df[c] = 0
        df = df[list(PRECIOS.keys())]  # ordenar columnas

        # NUEVO: Paquetes Día (suma de conteos)
        df["Paquetes Día"] = df[list(PRECIOS.keys())].sum(axis=1)

        # Total monetario del día
        df["Total $ Día"] = df.apply(lambda r: sum(PRECIOS[c] * r.get(c, 0) for c in PRECIOS), axis=1)

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", ".xlsx")])
        if path:
            df.to_excel(path)
            messagebox.showinfo("Éxito", f"Archivo guardado en {path}")

    # ---------------- Exportación detallada AGRUPADA (tipo Presis) ----------------
    def export_detallado_excel(self) -> None:
        rows = self._build_detalle_rows()
        if not rows:
            messagebox.showwarning("Sin datos", "No hay filas detalladas para exportar.")
            return

        df = pd.DataFrame(rows)
        group_cols = ["Fecha", "Día", "Cordón", "Localidad", "Domicilio", "Importe_unitario"]
        agg = df.groupby(group_cols, as_index=False).size().rename(columns={"size": "Cantidad"})
        agg["Cliente"] = "bazar gadol"
        agg["Importe"] = agg["Importe_unitario"] * agg["Cantidad"]

        # IDs simples correlativos
        agg = agg.reset_index(drop=True)
        agg["Remito"] = ["RM" + str(i + 1).zfill(8) for i in range(len(agg))]
        agg["Guía Agente"] = ["GA" + str(i + 1).zfill(8) for i in range(len(agg))]

        final_cols = ["Fecha", "Día", "Cliente", "Remito", "Guía Agente",
                      "Cordón", "Localidad", "Domicilio", "Cantidad", "Importe"]
        out = agg[final_cols]

        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", ".xlsx")])
        if path:
            out.to_excel(path, index=False)
            messagebox.showinfo("Éxito", f"Archivo detallado guardado en {path}")

    def export_detallado_markdown(self) -> None:
        rows = self._build_detalle_rows()
        if not rows:
            messagebox.showwarning("Sin datos", "No hay filas detalladas para exportar.")
            return

        df = pd.DataFrame(rows)
        group_cols = ["Fecha", "Día", "Cordón", "Localidad", "Domicilio", "Importe_unitario"]
        agg = df.groupby(group_cols, as_index=False).size().rename(columns={"size": "Cantidad"})
        agg["Cliente"] = "bazar gadol"
        agg["Importe"] = agg["Importe_unitario"] * agg["Cantidad"]

        final_cols = ["Fecha", "Día", "Cliente", "Cordón", "Localidad", "Domicilio", "Cantidad", "Importe"]
        out = agg[final_cols]

        md_parts = []
        md_parts.append("# 📦 Exportación detallada de entregas (agrupado)\n")
        md_parts.append(out.to_markdown(index=False, tablefmt="github"))

        path = filedialog.asksaveasfilename(defaultextension=".md", filetypes=[("Markdown", ".md")])
        if path:
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(md_parts))
            messagebox.showinfo("Éxito", f"Archivo Markdown guardado en {path}")

    # ---------------- Utilidades ----------------
    def _buscar_cordon_por_ciudad(self, ciudad: str) -> str:
        for c, lista in CORDONES.items():
            if ciudad and ciudad.upper() in lista:
                return c
        return "cordon_no_identificado"

    def _append_detalle(self, dia: str, cordon: str, ciudad: str, subregion: str,
                        src_path: str = "", manual: bool = False) -> None:
        from datetime import datetime as _dt
        row = {
            "Cordon": cordon,
            "Ciudad": (ciudad or ""),
            "Subregión": (subregion or ""),
            "Src": src_path or "",
            "Manual": bool(manual),
            "ts": _dt.now().isoformat(timespec="seconds"),
        }
        self.subregs[dia].append(row)

    def _migrate_subregs_schema(self):
        """
        Garantiza que cada entrada tenga: Cordon, Ciudad, Subregión, Src, Manual, ts
        y completa Cordon si falta (buscando por Ciudad).
        """
        changed = False
        for dia, items in self.subregs.items():
            new_items = []
            for s in items:
                cordon = s.get("Cordon")
                ciudad = s.get("Ciudad", "") or ""
                subreg = s.get("Subregión", "") or ""
                src = s.get("Src", "")
                manual = bool(s.get("Manual", False))
                ts = s.get("ts")

                if not cordon:
                    cordon = self._buscar_cordon_por_ciudad(ciudad)
                    if cordon not in PRECIOS:
                        cordon = "cordon_no_identificado"
                    changed = True

                if not ts:
                    from datetime import datetime as _dt
                    ts = _dt.now().isoformat(timespec="seconds")
                    changed = True

                new_items.append({
                    "Cordon": cordon,
                    "Ciudad": ciudad,
                    "Subregión": subreg,
                    "Src": src,
                    "Manual": manual,
                    "ts": ts,
                })
            self.subregs[dia] = new_items
        if changed:
            save_json(SUBREG_FILE, self.subregs)

    def _build_detalle_rows(self):
        """
        Devuelve lista de filas base para agrupar:
        [ {Fecha, Día, Cordón, Localidad, Domicilio, Importe_unitario}, ... ]
        """
        rows = []
        hoy = datetime.now().strftime("%d/%m/%Y")

        for dia, items in self.subregs.items():
            for s in items:
                cordon = s.get("Cordon") or self._buscar_cordon_por_ciudad(s.get("Ciudad", ""))
                if cordon not in PRECIOS:
                    cordon = "cordon_no_identificado"
                rows.append({
                    "Fecha": hoy,
                    "Día": dia,
                    "Cordón": cordon,
                    "Localidad": s.get("Ciudad", "") or "—",
                    "Domicilio": s.get("Subregión", "") or "—",
                    "Importe_unitario": PRECIOS.get(cordon, 0),
                })
        return rows

    # ---------------- Reset ----------------
    def reset_sem(self) -> None:
        if messagebox.askyesno("Confirmar", "¿Borrar todos los datos y pendientes?"):
            self.data = {d: {} for d in self.dias}
            self.subregs = {d: [] for d in self.dias}
            self.pendientes.clear()

            save_json(DATA_FILE, self.data)
            save_json(SUBREG_FILE, self.subregs)
            save_json(PEND_FILE, self.pendientes)

            self._render_tabla()
            self._render_pendientes()
            self._update_pend_count()

    def reset_dia(self) -> None:
        dia_sel = self.reset_dia_var.get()
        if dia_sel not in self.dias:
            messagebox.showwarning("Atención", "Seleccioná un día válido.")
            return

        if not messagebox.askyesno(
            "Confirmar",
            f"¿Resetear a cero los paquetes y el detallado de {dia_sel}?"
        ):
            return

        # Poner en cero el conteo y limpiar el detallado de ese día
        self.data[dia_sel] = {}
        self.subregs[dia_sel] = []

        # Persistir y refrescar UI
        save_json(DATA_FILE, self.data)
        save_json(SUBREG_FILE, self.subregs)

        self._render_tabla()
        # Pendientes no están asociados a día: se dejan tal cual

        messagebox.showinfo("Listo", f"Se reseteó {dia_sel}.")

    def _update_pend_count(self) -> None:
        self.lbl_pend.config(text=f"Pendientes: {len(self.pendientes)}")


if __name__ == "__main__":
    ClasificadorApp().mainloop()
