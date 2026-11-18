"""Two-column steganography GUI for message, file, and image-analysis workflows."""
import os
import random
import tkinter as tk
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

import steg_analysis as sa
import steg_core as sc

# NOTE: the algorithm is LSB (least-significant-bit). If your course requires
# the original wording, change APP_TITLE / BADGES / SUB_TEXT here.
APP_TITLE = "STEGANOGRAPHY TECHNIQUE USING LSB"
BADGES = "[ SECURE ]  [ LSB ]  [ PNG ]"
SUB_TEXT = "> hide_secrets.exe --mode=LSB --output=PNG"

DOWNLOAD_DIR = os.path.join(os.path.expanduser("~"), "Downloads")
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# ---- colours / fonts (same palette as main.py) -----------------------------
BG, PANEL, INNER, MUTED = "#04060d", "#0a0f1c", "#03050a", "#5c6b8a"
NEON_CYAN, NEON_GREEN, NEON_PINK, NEON_YELLOW = "#00f5ff", "#39ff14", "#ff2bd6", "#ffe600"
FONT_CARD = ("Consolas", 10, "bold")
FONT_BTN = ("Consolas", 10, "bold")
FONT_TEXT = ("Consolas", 10)
RAIN_CHARS = "01<>/{}[]#$%&*+="
RAIN_SHADES = ["#39ff14", "#1fa80c", "#147008", "#0d4a06", "#093304", "#062203"]

PREVIEW_W, PREVIEW_H = 300, 190


def _hex_to_rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


class StegoApp:
    def __init__(self, root):
        self.root = root
        self.image_path = ""
        self.opened_path = ""
        self.encoded_path = os.path.join(DOWNLOAD_DIR, "stegno.png")
        self.capacity_bytes = 0
        self.rain_cols = []
        self.header_state = {"typed": 0, "tick": 0}

        root.title(APP_TITLE)
        root.geometry("1240x860")
        root.minsize(1080, 740)
        root.configure(bg=BG)

        self.password_var = tk.StringVar(value="")
        self.random_var = tk.BooleanVar(value=False)
        self.show_pw_var = tk.BooleanVar(value=False)
        self.capacity_var = tk.StringVar(value="CAPACITY: select an image")

        self._build_header()
        self._build_status_bar()
        self._build_options()

        self.workspace = tk.Frame(root, bg=BG)
        self.workspace.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.left_panel = tk.Frame(self.workspace, bg=BG)
        self.left_panel.pack(side="left", fill="both", expand=True, padx=(0, 5))
        self.right_panel = tk.Frame(self.workspace, bg=BG)
        self.right_panel.pack(side="left", fill="both", expand=True, padx=(5, 0))

        self._build_left_panel()
        self._build_right_panel()
        self._animate_header()

    # ------------------------------------------------------------------ UI
    def _build_header(self):
        self.header = tk.Canvas(self.root, height=84, bg=BG, highlightthickness=0, bd=0)
        self.header.pack(fill="x")
        self.header.bind("<Configure>", self._draw_header)

    def _draw_header(self, event=None):
        c = self.header
        c.delete("all")
        w, h = c.winfo_width(), c.winfo_height()
        if w <= 2 or h <= 2:
            return
        c.create_rectangle(0, 0, w, h, fill=BG, outline="")
        c.create_rectangle(14, h // 2 - 34, min(700, w - 20), h // 2 + 32,
                           fill=BG, outline=NEON_CYAN, width=1, tags="titlebg")
        for dx, dy in ((-2, 0), (2, 0), (0, -2), (0, 2)):
            c.create_text(30 + dx, h // 2 - 12 + dy, text=APP_TITLE, anchor="w",
                          fill="#0b5560", font=("Consolas", 20, "bold"))
        c.create_text(30, h // 2 - 12, text=APP_TITLE, anchor="w",
                      fill=NEON_CYAN, font=("Consolas", 20, "bold"))
        c.create_text(w - 20, 20, text=BADGES, anchor="e", fill=NEON_PINK,
                      font=("Consolas", 10, "bold"))
        c1, c2 = _hex_to_rgb(NEON_CYAN), _hex_to_rgb(NEON_PINK)
        for x in range(0, w, 4):
            t = x / max(1, w)
            r, g, b = (round(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))
            c.create_rectangle(x, h - 3, x + 4, h, outline="", fill=f"#{r:02x}{g:02x}{b:02x}")

    def _animate_header(self):
        c = self.header
        w, h = c.winfo_width(), c.winfo_height()
        if w > 2 and h > 2:
            n = max(1, w // 14)
            if len(self.rain_cols) != n:
                self.rain_cols = [[random.randint(-h, h), random.randint(4, 9)] for _ in range(n)]
            c.delete("rain")
            c.delete("sub")
            for i, col in enumerate(self.rain_cols):
                x = i * 14 + 7
                for k, shade in enumerate(RAIN_SHADES):
                    cy = col[0] - k * 14
                    if 0 <= cy <= h - 4:
                        c.create_text(x, cy, text=random.choice(RAIN_CHARS), fill=shade,
                                      font=("Consolas", 10), tags="rain")
                col[0] += col[1]
                if col[0] - len(RAIN_SHADES) * 14 > h:
                    col[0], col[1] = random.randint(-60, 0), random.randint(4, 9)
            st = self.header_state
            st["tick"] += 1
            if st["typed"] < len(SUB_TEXT) and st["tick"] % 2 == 0:
                st["typed"] += 1
            cursor = "█" if (st["tick"] // 6) % 2 == 0 else " "
            c.create_text(32, h // 2 + 16, text=SUB_TEXT[:st["typed"]] + cursor, anchor="w",
                          fill=NEON_GREEN, font=("Consolas", 10), tags="sub")
            c.tag_raise("titlebg")
            c.tag_raise("sub")
        self.root.after(80, self._animate_header)

    @staticmethod
    def _neon_button(parent, text, command, color, width=160):
        wrap = tk.Frame(parent, bg=color, width=width, height=44)
        wrap.pack_propagate(False)
        btn = tk.Button(wrap, text=text, command=command, bg=PANEL, fg=color,
                        activebackground=color, activeforeground=BG, font=FONT_BTN,
                        relief="flat", bd=0, cursor="hand2")
        btn.pack(fill="both", expand=True, padx=1, pady=1)
        btn.bind("<Enter>", lambda e: btn.configure(bg=color, fg=BG))
        btn.bind("<Leave>", lambda e: btn.configure(bg=PANEL, fg=color))
        return wrap, btn

    @staticmethod
    def _neon_card(parent, title, color):
        return tk.LabelFrame(parent, text=f" [ {title} ] ", font=FONT_CARD, bg=PANEL, fg=color,
                             bd=0, relief="flat", highlightthickness=1,
                             highlightbackground=color, highlightcolor=color, labelanchor="nw")

    def _build_left_panel(self):
        tk.Label(self.left_panel, text="MESSAGE WORKFLOW", bg=BG, fg=NEON_CYAN,
                 font=("Consolas", 12, "bold")).pack(anchor="w", padx=8, pady=(6, 4))

        actions = tk.Frame(self.left_panel, bg=PANEL, height=54)
        actions.pack(fill="x", pady=4)
        actions.pack_propagate(False)
        for text, command, color in (
            ("SELECT IMAGE", self.select_input_image, NEON_CYAN),
            ("ENCODE TEXT", self.encode_text_message, NEON_GREEN),
            ("DECODE MESSAGE", self.decode_message, NEON_PINK),
        ):
            wrap, _ = self._neon_button(actions, text, command, color, width=150)
            wrap.pack(side="left", padx=8, pady=5)

        previews = tk.Frame(self.left_panel, bg=BG, height=236)
        previews.pack(fill="x", pady=4)
        previews.pack_propagate(False)
        self.input_card = self._neon_card(previews, "INPUT IMAGE", NEON_CYAN)
        self.encoded_card = self._neon_card(previews, "ENCODED IMAGE", NEON_PINK)
        for card in (self.input_card, self.encoded_card):
            card.pack(side="left", padx=5, fill="both", expand=True)
        self.input_image_label = self._placeholder(
            self.input_card, "[ NO IMAGE LOADED ]\n\n> select an image"
        )
        self.encoded_image_label = self._placeholder(
            self.encoded_card, "[ AWAITING OUTPUT ]\n\n> encode text or a file"
        )

        messages = tk.Frame(self.left_panel, bg=BG)
        messages.pack(fill="both", expand=True, pady=4)
        self.input_message_text = self._text_card(
            messages, "SECRET MESSAGE", NEON_GREEN, NEON_GREEN, False
        )
        self.input_message_text.bind("<KeyRelease>", lambda e: self._update_capacity())
        self.decoded_text = self._text_card(
            messages, "DECODED MESSAGE", NEON_YELLOW, NEON_YELLOW, True
        )

    def _build_options(self):
        opt = tk.Frame(self.root, bg=PANEL, height=46)
        opt.pack(fill="x", padx=8, pady=(0, 5))
        opt.pack_propagate(False)
        tk.Label(opt, text="PASSWORD ❯", bg=PANEL, fg=NEON_CYAN, font=FONT_CARD).pack(side="left", padx=(12, 6))
        self.pw_entry = tk.Entry(opt, textvariable=self.password_var, show="*", width=22,
                                 bg=INNER, fg=NEON_GREEN, insertbackground=NEON_GREEN,
                                 relief="flat", font=FONT_TEXT)
        self.pw_entry.pack(side="left", padx=4, ipady=3)
        tk.Checkbutton(opt, text="show", variable=self.show_pw_var, command=self._toggle_password,
                       bg=PANEL, fg=MUTED, selectcolor=INNER, activebackground=PANEL,
                       activeforeground=NEON_CYAN, font=("Consolas", 9)).pack(side="left", padx=4)
        tk.Checkbutton(opt, text="RANDOM PIXEL POSITIONS (needs password)", variable=self.random_var,
                       bg=PANEL, fg=NEON_PINK, selectcolor=INNER, activebackground=PANEL,
                       activeforeground=NEON_PINK, font=FONT_CARD).pack(side="left", padx=18)
        self.capacity_label = tk.Label(opt, textvariable=self.capacity_var, bg=PANEL,
                                       fg=NEON_GREEN, font=FONT_CARD)
        self.capacity_label.pack(side="right", padx=12)

    def _build_right_panel(self):
        tk.Label(self.right_panel, text="FILE & ANALYSIS WORKFLOW", bg=BG, fg=NEON_PINK,
                 font=("Consolas", 12, "bold")).pack(anchor="w", padx=8, pady=(6, 4))

        actions = tk.Frame(self.right_panel, bg=PANEL, height=54)
        actions.pack(fill="x", pady=4)
        actions.pack_propagate(False)
        for text, command, color in (
            ("OPEN FILE", self.open_file, NEON_CYAN),
            ("HIDE FILE", self.encode_file_payload, NEON_GREEN),
            ("DETECT PROCESS", self.detect_image, NEON_YELLOW),
        ):
            wrap, _ = self._neon_button(actions, text, command, color, width=145)
            wrap.pack(side="left", padx=5, pady=5)

        self.opened_file_var = tk.StringVar(value="No file opened")
        tk.Label(self.right_panel, textvariable=self.opened_file_var, bg=INNER, fg=NEON_GREEN,
                 font=("Consolas", 9), wraplength=540, justify="left", anchor="w",
                 padx=8, pady=6).pack(fill="x", pady=(2, 5))

        previews = tk.Frame(self.right_panel, bg=BG, height=236)
        previews.pack(fill="x", pady=4)
        previews.pack_propagate(False)
        self.opened_card = self._neon_card(previews, "OPENED FILE", NEON_CYAN)
        self.map_card = self._neon_card(previews, "LSB / CHANGE MAP", NEON_YELLOW)
        for card in (self.opened_card, self.map_card):
            card.pack(side="left", padx=5, fill="both", expand=True)
        self.opened_image_label = self._placeholder(
            self.opened_card, "[ NO FILE OPENED ]\n\n> open an image to decode or detect"
        )
        self.map_image_label = self._placeholder(
            self.map_card, "[ NO ANALYSIS ]\n\n> detect or encode to fill"
        )

        self.report_text = self._text_card(
            self.right_panel, "ANALYSIS REPORT", NEON_CYAN, NEON_CYAN, True, width=44
        )

    @staticmethod
    def _placeholder(card, text):
        lab = tk.Label(card, text=text, font=FONT_TEXT, bg=INNER, fg=MUTED, anchor="center")
        lab.pack(pady=8, padx=8, fill="both", expand=True)
        return lab

    def _text_card(self, parent, title, color, fg, readonly, width=30):
        card = self._neon_card(parent, title, color)
        card.pack(side="left", padx=6, fill="both", expand=True)
        txt = tk.Text(card, height=10, width=width, bg=INNER, fg=fg, font=FONT_TEXT,
                      insertbackground=fg, insertwidth=2, selectbackground="#0b5560",
                      selectforeground="white", relief="flat", bd=0, padx=8, pady=8, wrap="word")
        if readonly:
            txt.configure(state="disabled")
        txt.pack(pady=8, padx=8, fill="both", expand=True)
        return txt

    def _build_status_bar(self):
        bar = tk.Frame(self.root, bg=PANEL, height=30)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        tk.Frame(bar, bg=NEON_CYAN, height=1).pack(fill="x")
        tk.Label(bar, text="  ❯", font=("Consolas", 11, "bold"), bg=PANEL, fg=NEON_PINK).pack(side="left")
        self.status_label = tk.Label(bar, text="Ready", font=("Consolas", 10), bg=PANEL,
                                     fg=NEON_GREEN, anchor="w", padx=6)
        self.status_label.pack(side="left", fill="x", expand=True)
        tk.Label(bar, text="LSB STEGANOGRAPHY  •  PNG OUTPUT  •  AES-FERNET  ", font=("Consolas", 9),
                 bg=PANEL, fg=MUTED).pack(side="right")

    # ------------------------------------------------------------- helpers
    def _status(self, text, color=NEON_GREEN):
        self.status_label.configure(text=text, fg=color)
        self.root.update_idletasks()

    def _toggle_password(self):
        self.pw_entry.configure(show="" if self.show_pw_var.get() else "*")

    @staticmethod
    def _set_text(widget, text):
        widget.configure(state="normal")
        widget.delete("1.0", "end")
        widget.insert("1.0", text)
        widget.configure(state="disabled")

    def _show_pil(self, pil_img, label):
        photo = ImageTk.PhotoImage(pil_img)
        label.configure(image=photo, text="")
        label.image = photo                        # keep a reference

    def _show_file(self, path, label):
        with Image.open(path) as src:
            img = src.convert("RGB")
        scale = min(PREVIEW_W / img.width, PREVIEW_H / img.height, 1.0)
        size = (max(1, round(img.width * scale)), max(1, round(img.height * scale)))
        self._show_pil(img.resize(size, Image.Resampling.LANCZOS), label)

    def _password(self):
        return self.password_var.get() or None

    def _update_capacity(self):
        if not self.capacity_bytes:
            self.capacity_var.set("TEXT CAPACITY: select an image")
            return
        used = len(self.input_message_text.get("1.0", "end-1c").encode("utf-8"))
        pct = 100.0 * used / self.capacity_bytes
        self.capacity_var.set(f"TEXT CAPACITY: {used} / {self.capacity_bytes} bytes ({pct:.1f}%)")
        self.capacity_label.configure(fg=NEON_PINK if used > self.capacity_bytes else NEON_GREEN)

    # ------------------------------------------------------------ commands
    def select_input_image(self):
        path = filedialog.askopenfilename(
            title="Select input image",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        if not path:
            return
        try:
            info = sc.image_capacity(path)
            if info is None:
                raise sc.StegoError("Could not read this image.")
            self.image_path = path
            self._show_file(path, self.input_image_label)
        except Exception as e:
            messagebox.showerror("Error", f"Could not load image:\n{e}")
            return
        w, h, cap = info
        self.capacity_bytes = cap
        self._update_capacity()
        self._status(f"Selected: {os.path.basename(path)}  ({w}x{h} px)")

    def open_file(self):
        path = filedialog.askopenfilename(
            title="Open image to decode or analyse",
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        if path:
            self._set_opened_file(path)

    def _set_opened_file(self, path):
        try:
            self._show_file(path, self.opened_image_label)
        except (OSError, ValueError) as e:
            messagebox.showerror("Open File Error", f"Could not open image:\n{e}")
            return False
        self.opened_path = path
        self.opened_file_var.set(os.path.basename(path) + "\n" + path)
        self._status(f"Opened: {os.path.basename(path)}")
        return True

    def _ask_output(self):
        out = filedialog.asksaveasfilename(
            title="Save encoded stego image", initialdir=DOWNLOAD_DIR, initialfile="stegno.png",
            defaultextension=".png", filetypes=[("PNG images", "*.png"), ("All files", "*.*")])
        return os.path.splitext(out)[0] + ".png" if out else None

    def _encode(self, build_payload, what):
        if not self.image_path:
            messagebox.showerror("Error", "Please select an image first.")
            return
        password, rnd = self._password(), self.random_var.get()
        if rnd and not password:
            messagebox.showerror("Error", "Random pixel positions need a password.\nType one in the PASSWORD box.")
            return
        payload = build_payload()
        if payload is None:
            return

        # Preflight capacity check: detect oversized text/files before asking
        # the user where to save the output or attempting embedding.
        try:
            cover = sc.load_image(self.image_path)
            max_bytes = sc.max_plaintext_bytes(cover.shape)
        except (sc.StegoError, OSError, ValueError) as e:
            messagebox.showerror("Image Error", f"Could not check image capacity:\n{e}")
            self._status("Capacity check failed", NEON_PINK)
            return

        payload_bytes = len(payload)
        if payload_bytes > max_bytes:
            over_by = payload_bytes - max_bytes
            ratio = payload_bytes / max_bytes if max_bytes else float("inf")
            messagebox.showerror(
                "Payload Too Large",
                "The selected image cannot hold this payload.\n\n"
                f"Payload size: {payload_bytes:,} bytes "
                f"({payload_bytes / 1024:.1f} KiB)\n"
                f"Image capacity: {max_bytes:,} bytes "
                f"({max_bytes / 1024:.1f} KiB)\n"
                f"Over capacity by: {over_by:,} bytes\n\n"
                f"Your payload is about {ratio:.2f} times the available capacity.\n\n"
                "Try one of these options:\n"
                "• Choose a larger cover image.\n"
                "• Select a smaller file or shorter message.\n"
                "• Compress the file first (if it can be compressed)."
            )
            self._status(
                f"Payload too large: {payload_bytes:,} / {max_bytes:,} bytes",
                NEON_PINK
            )
            return

        # Show a useful status before asking for the output path.
        self._status(
            f"Payload fits: {payload_bytes:,} / {max_bytes:,} bytes "
            f"({100 * payload_bytes / max_bytes:.1f}%)"
        )
        out = self._ask_output()
        if not out:
            self._status("Encoding cancelled")
            return
        try:
            self._status(f"Encoding {what}...")
            res = sc.embed_and_save(self.image_path, payload, out, password, rnd)
        except (sc.StegoError, OSError) as e:
            self._status("Encoding failed", NEON_PINK)
            messagebox.showerror("Error", f"Encoding failed:\n{e}")
            return
        self.encoded_path = out
        self._show_file(out, self.encoded_image_label)
        self.map_card.configure(text=" [ CHANGE MAP ] ")
        self._show_pil(sc.density_preview(sc.difference_mask(res.cover, res.stego),
                                          PREVIEW_W, PREVIEW_H), self.map_image_label)
        self._set_text(self.report_text, self._encode_report(res))
        self._status("Saved PNG: " + os.path.abspath(out))
        messagebox.showinfo("Success", f"{what.capitalize()} encoded successfully!\n\nSaved to:\n{os.path.abspath(out)}")

    def _encode_report(self, res):
        m = res.metrics
        before = sa.analyze_array(res.cover)
        after = sa.analyze_array(res.stego)

        def ml(r):
            return f"{r['model'][1] * 100:.1f}%" if r["model"] else "n/a"
        return "\n".join([
            "ENCODE REPORT", "-" * 34,
            f"Mode         : {res.mode}",
            f"Bits used    : {res.bits_used} of {res.capacity_bits} ({100 * res.bits_used / res.capacity_bits:.3f}%)",
            f"MSE          : {m['mse']:.6f}",
            f"PSNR         : {m['psnr']:.2f} dB",
            f"SSIM         : {m['ssim']:.6f}",
            f"Samples changed: {m['samples_changed']} / {m['samples_total']}", "",
            "DETECTION  (original -> encoded)", "-" * 34,
            f"Verdict      : {before['verdict']} -> {after['verdict']}",
            f"ML P[stego]  : {ml(before)} -> {ml(after)}",
            f"Signature    : {'found' if after['signature']['found'] else 'not found'}",
            f"Reason       : {after['reason']}",
        ])

    def encode_text_message(self):
        def build():
            msg = self.input_message_text.get("1.0", "end-1c").strip()
            if not msg:
                messagebox.showerror("Error", "Please enter a secret message.")
                return None
            return sc.pack_text(msg)
        self._encode(build, "message")

    def encode_file_payload(self):
        def build():
            path = filedialog.askopenfilename(title="Choose the file to hide")
            if not path:
                return None
            try:
                return sc.pack_file(path)
            except (OSError, sc.StegoError) as e:
                messagebox.showerror("Error", f"Could not read file:\n{e}")
                return None
        self._encode(build, "file")

    def decode_message(self):
        path = filedialog.askopenfilename(
            title="Open encoded image", initialdir=DOWNLOAD_DIR,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        if not path or not self._set_opened_file(path):
            return
        try:
            self._status("Decoding...")
            result = sc.decode(path, self._password())
        except (sc.StegoError, OSError) as e:
            self._status("No hidden message found / cannot decrypt", NEON_PINK)
            messagebox.showerror("Decode Error", str(e))
            return
        if result.kind == "text":
            self._set_text(self.decoded_text, result.text)
            self._status("Message decoded successfully")
            messagebox.showinfo("Success", "Message decoded successfully!")
            return
        dest = filedialog.asksaveasfilename(title="Save the extracted file", initialdir=DOWNLOAD_DIR,
                                            initialfile=result.filename)
        if not dest:
            self._set_text(self.decoded_text, f"[FILE] {result.filename} ({len(result.data)} bytes)\nnot saved")
            return
        with open(dest, "wb") as f:
            f.write(result.data)
        self._set_text(self.decoded_text, f"[FILE] {result.filename} ({len(result.data)} bytes)\nsaved to:\n{dest}")
        self._status("Hidden file extracted: " + dest)
        messagebox.showinfo("Success", f"Hidden file extracted:\n{dest}")

    def detect_image(self):
        start = os.path.dirname(self.opened_path) if self.opened_path else DOWNLOAD_DIR
        path = filedialog.askopenfilename(
            title="Choose an image to analyse", initialdir=start,
            filetypes=[("Image files", "*.png *.jpg *.jpeg *.bmp"), ("All files", "*.*")])
        if not path or not self._set_opened_file(path):
            return
        try:
            self._status("Analysing image...")
            result = sa.analyze_file(path)
            self.map_card.configure(text=" [ LSB PLANE ] ")
            self._show_pil(sc.lsb_plane_preview(sc.load_image(path), PREVIEW_W, PREVIEW_H),
                           self.map_image_label)
        except (OSError, FileNotFoundError, sc.StegoError) as e:
            messagebox.showerror("Error", f"Could not analyse image:\n{e}")
            return
        self._set_text(self.report_text, sa.format_report(os.path.basename(path), result))
        self._status(f"Detection: {result['verdict']} ({result['confidence']} confidence)",
                     NEON_PINK if result["verdict"] != "CLEAN" else NEON_GREEN)


def main():
    root = tk.Tk()
    StegoApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
