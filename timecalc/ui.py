"""Tkinter user interface, laid out to match the supplied screenshot."""
from __future__ import annotations

import calendar
import datetime as dt
import tkinter as tk
from tkinter import messagebox, ttk

from . import core, mailer
from . import settings as settings_store

FONT = "Segoe UI"
BLUE, RED, GREEN, GREY = "#4F6BAE", "#E0645A", "#1B6B17", "#9E9E9E"
PANEL_BG, BORDER, ENTRY_BORDER = "#F6F6F6", "#D2D2D2", "#CFCFCF"
INVALID, TEXT, MUTED = "#D9534F", "#333333", "#666666"
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
DAY_NAMES = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

SCALE = 1.0   # set at start-up from the screen DPI so the fixed layout scales cleanly


def px(v: float) -> int:
    return int(round(v * SCALE))


def put(widget, x, y, w=None, h=None, anchor="nw"):
    """place() with design-pixel coordinates (taken from the screenshot) scaled for DPI."""
    kw = {"x": px(x), "y": px(y), "anchor": anchor}
    if w is not None:
        kw["width"] = px(w)
    if h is not None:
        kw["height"] = px(h)
    widget.place(**kw)


def darken(hex_colour: str, factor: float = 0.88) -> str:
    r, g, b = (int(hex_colour[i:i + 2], 16) for i in (1, 3, 5))
    return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))


def make_button(parent, text, command, bg, fg="white", font=None, **kw):
    b = tk.Button(parent, text=text, command=command, bg=bg, fg=fg, font=font,
                  activebackground=darken(bg), activeforeground=fg, relief="flat", bd=0,
                  highlightthickness=0, cursor="hand2", takefocus=1, **kw)
    b._base = bg
    b.bind("<Enter>", lambda e: b.configure(bg=darken(b._base)))
    b.bind("<Leave>", lambda e: b.configure(bg=b._base))
    return b


def recolor(button, bg, fg="white"):
    button._base = bg
    button.configure(bg=bg, fg=fg, activebackground=darken(bg), activeforeground=fg)


# =========================================================================== #
# Calendar pop-up
# =========================================================================== #
class CalendarPopup(tk.Toplevel):
    def __init__(self, app, anchor, initial: dt.date, on_pick):
        super().__init__(app)
        self.on_pick, self.selected = on_pick, initial
        self.view = (initial.year, initial.month)
        self.title("Pick a date")
        self.configure(bg="white", padx=8, pady=8)
        self.resizable(False, False)
        self.transient(app)
        head = tk.Frame(self, bg="white")
        head.pack(fill="x")
        for text, delta in (("«", -12), ("‹", -1)):
            make_button(head, text, lambda d=delta: self._shift(d), "#EEEEEE", TEXT, width=3).pack(side="left", padx=1)
        for text, delta in (("»", 12), ("›", 1)):
            make_button(head, text, lambda d=delta: self._shift(d), "#EEEEEE", TEXT, width=3).pack(side="right", padx=1)
        self.caption = tk.Label(head, bg="white", fg=TEXT, font=(FONT, 10, "bold"))
        self.caption.pack(side="left", expand=True)
        self.grid_frame = tk.Frame(self, bg="white")
        self.grid_frame.pack(pady=(6, 4))
        make_button(self, "Today", lambda: self._choose(dt.date.today()), BLUE, padx=10, pady=3).pack()
        self._render()
        self.geometry(f"+{anchor.winfo_rootx()}+{anchor.winfo_rooty() + anchor.winfo_height() + 4}")
        self.bind("<Escape>", lambda e: self.destroy())
        self.grab_set()
        self.focus_set()

    def _shift(self, months):
        y, m = self.view
        idx = y * 12 + m - 1 + months
        y, m = divmod(idx, 12)
        self.view = (min(max(y, core.MIN_YEAR), core.MAX_YEAR), m + 1)
        self._render()

    def _render(self):
        y, m = self.view
        self.caption.configure(text=f"{calendar.month_name[m]} {y}")
        for child in self.grid_frame.winfo_children():
            child.destroy()
        for c, name in enumerate(DAY_NAMES):
            tk.Label(self.grid_frame, text=name, bg="white", fg=MUTED, font=(FONT, 8), width=4).grid(row=0, column=c)
        today = dt.date.today()
        for r, week in enumerate(calendar.Calendar(0).monthdayscalendar(y, m), start=1):
            for c, day in enumerate(week):
                if not day:
                    continue
                d = dt.date(y, m, day)
                is_sel = d == self.selected
                b = make_button(self.grid_frame, str(day), lambda d=d: self._choose(d),
                                BLUE if is_sel else "white", "white" if is_sel else TEXT,
                                font=(FONT, 9, "bold" if d == today else "normal"), width=4)
                b.grid(row=r, column=c, padx=1, pady=1)

    def _choose(self, d):
        self.destroy()
        self.on_pick(d)


# =========================================================================== #
# Option dialogs
# =========================================================================== #
class _Dialog(tk.Toplevel):
    def __init__(self, app, title, on_save):
        super().__init__(app)
        self.app, self.on_save = app, on_save
        self.title(title)
        self.configure(bg="white", padx=18, pady=14)
        self.transient(app)
        self.resizable(False, False)
        body = tk.Frame(self, bg="white")
        body.pack(fill="both", expand=True)
        self._build(body)
        bar = tk.Frame(self, bg="white")
        bar.pack(fill="x", pady=(14, 0))
        make_button(bar, "Reset to defaults", self._reset, "#EEEEEE", TEXT, padx=10, pady=5).pack(side="left")
        make_button(bar, "OK", self._ok, BLUE, padx=22, pady=5).pack(side="right")
        make_button(bar, "Cancel", self.destroy, "#EEEEEE", TEXT, padx=14, pady=5).pack(side="right", padx=8)
        self.bind("<Escape>", lambda e: self.destroy())
        self.update_idletasks()
        x = app.winfo_rootx() + (app.winfo_width() - self.winfo_width()) // 2
        y = app.winfo_rooty() + 60
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        self.grab_set()
        self.focus_set()

    def _ok(self):
        if self._apply():
            self.destroy()

    def _build(self, body): ...
    def _apply(self) -> bool: ...
    def _reset(self): ...


def _group(parent, title):
    box = tk.LabelFrame(parent, text=title, bg="white", fg=TEXT, font=(FONT, 9, "bold"), padx=10, pady=6)
    box.pack(fill="x", pady=(0, 10))
    return box


class HoursOptionsDialog(_Dialog):
    def __init__(self, app, opts: core.HoursOptions, on_save):
        self.opts = opts
        super().__init__(app, "Time Between Hours - More Options", on_save)

    def _build(self, body):
        o = self.opts
        self.output = tk.StringVar(value=o.output)
        self.overnight = tk.BooleanVar(value=o.overnight)
        self.brk = tk.StringVar(value=str(o.break_minutes))
        g = _group(body, "Show the total as")
        for text, val in (("Decimal hours (e.g. 07.50)", "decimal"), ("Hours and minutes (e.g. 07:30)", "hhmm")):
            tk.Radiobutton(g, text=text, variable=self.output, value=val, bg="white", font=(FONT, 10),
                           activebackground="white", anchor="w").pack(fill="x")
        g = _group(body, "Rules")
        tk.Checkbutton(g, text="If 'To' is earlier than 'From', count it as the next day (overnight)",
                       variable=self.overnight, bg="white", font=(FONT, 10), activebackground="white").pack(anchor="w")
        row = tk.Frame(g, bg="white")
        row.pack(anchor="w", pady=(6, 0))
        tk.Label(row, text="Unpaid break to subtract (minutes):", bg="white", font=(FONT, 10)).pack(side="left")
        tk.Entry(row, textvariable=self.brk, width=6, justify="center", font=(FONT, 10)).pack(side="left", padx=6)

    def _apply(self):
        try:
            brk = core.parse_field(self.brk.get(), "Break", 0, 1440)
        except core.ValidationError as err:
            messagebox.showerror("Invalid value", str(err), parent=self)
            return False
        self.on_save(core.HoursOptions(self.output.get(), self.overnight.get(), brk))
        return True

    def _reset(self):
        d = core.HoursOptions()
        self.output.set(d.output)
        self.overnight.set(d.overnight)
        self.brk.set(str(d.break_minutes))


class DateOptionsDialog(_Dialog):
    def __init__(self, app, opts: core.DateOptions, on_save):
        self.opts = opts
        super().__init__(app, "Time Between Dates - More Options", on_save)

    def _build(self, body):
        o = self.opts
        self.mode = tk.StringVar(value=o.mode)
        self.inc_start = tk.BooleanVar(value=o.include_start)
        self.inc_end = tk.BooleanVar(value=o.include_end)
        self.skip_hol = tk.BooleanVar(value=o.skip_holidays)
        self.output = tk.StringVar(value=o.output)
        self.weekend = [tk.BooleanVar(value=i in o.weekend_days) for i in range(7)]

        def radio(parent, text, var, val):
            tk.Radiobutton(parent, text=text, variable=var, value=val, bg="white", font=(FONT, 10),
                           activebackground="white", anchor="w").pack(fill="x")

        g = _group(body, "Count")
        radio(g, "Calendar days", self.mode, "calendar")
        radio(g, "Working days (skip weekend days and holidays)", self.mode, "working")

        g = _group(body, "Inclusive-date rules")
        for text, var in (("Include the start date (From)", self.inc_start),
                          ("Include the end date (To)", self.inc_end)):
            tk.Checkbutton(g, text=text, variable=var, bg="white", font=(FONT, 10),
                           activebackground="white").pack(anchor="w")
        tk.Label(g, text="Default: start included, end excluded (Oct 13 -> Nov 13 = 31 days).\n"
                         "Include both = 32, exclude both = 30.", bg="white", fg=MUTED,
                 font=(FONT, 8), justify="left").pack(anchor="w", pady=(4, 0))

        g = _group(body, "Weekend days (used by working days)")
        row = tk.Frame(g, bg="white")
        row.pack(anchor="w")
        for i, name in enumerate(DAY_NAMES):
            tk.Checkbutton(row, text=name, variable=self.weekend[i], bg="white", font=(FONT, 9),
                           activebackground="white").pack(side="left")

        g = _group(body, "Holidays (used by working days)")
        tk.Checkbutton(g, text="Skip these dates", variable=self.skip_hol, bg="white", font=(FONT, 10),
                       activebackground="white").pack(anchor="w")
        tk.Label(g, text="One date per line, format YYYY-MM-DD", bg="white", fg=MUTED,
                 font=(FONT, 8)).pack(anchor="w")
        self.hol_text = tk.Text(g, width=30, height=5, font=("Consolas", 10), relief="solid", bd=1)
        self.hol_text.pack(anchor="w", pady=(2, 0))
        self.hol_text.insert("1.0", core.format_holidays(o.holidays))

        g = _group(body, "Show calendar-day totals as")
        radio(g, "Days", self.output, "days")
        radio(g, "Weeks and days", self.output, "weeks_days")
        radio(g, "Years, months and days", self.output, "ymd")

    def _apply(self):
        try:
            holidays = core.parse_holidays(self.hol_text.get("1.0", "end"))
        except core.ValidationError as err:
            messagebox.showerror("Invalid holiday", str(err), parent=self)
            return False
        weekend = frozenset(i for i, v in enumerate(self.weekend) if v.get())
        if self.mode.get() == "working" and len(weekend) == 7:
            messagebox.showerror("Invalid weekend", "At least one day of the week must be a working day.", parent=self)
            return False
        self.on_save(core.DateOptions(self.mode.get(), self.inc_start.get(), self.inc_end.get(),
                                      weekend, holidays, self.skip_hol.get(), self.output.get()))
        return True

    def _reset(self):
        d = core.DateOptions()
        self.mode.set(d.mode)
        self.inc_start.set(d.include_start)
        self.inc_end.set(d.include_end)
        self.skip_hol.set(d.skip_holidays)
        self.output.set(d.output)
        for i, v in enumerate(self.weekend):
            v.set(i in d.weekend_days)
        self.hol_text.delete("1.0", "end")


# =========================================================================== #
# Main window
# =========================================================================== #
class TimeCalculatorApp(tk.Tk):
    VISIBLE_ROWS, ROW_H, MAX_ROWS = 10, 48, 60

    def __init__(self):
        super().__init__()
        global SCALE
        SCALE = max(1.0, self.winfo_fpixels("1i") / 96.0)
        self.title("Time Calculator")
        self.configure(bg="white")
        self.resizable(False, False)
        self.geometry(f"{px(790)}x{px(692)}")

        self.settings = settings_store.load()
        self.f_head = (FONT, 11)
        self.f_body = (FONT, 11)
        self.f_small = (FONT, 10)
        self.f_entry = (FONT, 12)
        self.f_btn = (FONT, 10)
        self._vcmd = self.register(self._digits_only)
        self._marked = []
        self._calc_buttons = {}
        self._panel_actions = []
        self.rows = []

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground="white", background="white", foreground=TEXT,
                        bordercolor=ENTRY_BORDER, lightcolor="white", darkcolor="white",
                        arrowcolor="#222222", padding=4)
        style.map("TCombobox", fieldbackground=[("readonly", "white")],
                  selectbackground=[("readonly", "white")], selectforeground=[("readonly", TEXT)])
        style.configure("Invalid.TCombobox", fieldbackground="white", background="white",
                        bordercolor=INVALID, lightcolor=INVALID, darkcolor=INVALID, arrowcolor="#222222", padding=4)
        style.map("Invalid.TCombobox", fieldbackground=[("readonly", "white")])
        self.option_add("*TCombobox*Listbox.font", self.f_body)

        self._build_sum_panel()
        self._build_total_panel()
        connector = tk.Frame(self, bg=BLUE)
        put(connector, 200, 38, 38, 10)
        self._build_hours_panel()
        self._build_dates_panel()

        self.status = tk.Label(self, text="", bg="white", fg=MUTED, font=(FONT, 9), anchor="w", justify="left")
        put(self.status, 22, 656, 745, 28)
        self.bind("<Return>", self._on_enter)
        self.bind_all("<MouseWheel>", self._on_wheel)

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _digits_only(proposed, maxlen):
        return proposed == "" or (proposed.isascii() and proposed.isdigit() and len(proposed) <= int(maxlen))

    def _panel(self, x, y, w, h, title, colour, anchor="center"):
        frame = tk.Frame(self, bg=PANEL_BG, highlightthickness=1, highlightbackground=BORDER)
        put(frame, x, y, w, h)
        head = tk.Label(frame, text=title, bg=colour, fg="white", font=self.f_head, anchor=anchor,
                        padx=px(15) if anchor == "w" else 0)
        put(head, 0, 0, w - 2, 50)
        return frame

    def _box(self, parent, var, maxlen):
        e = tk.Entry(parent, textvariable=var, justify="center", font=self.f_entry, bg="white", fg=TEXT,
                     relief="flat", bd=0, highlightthickness=1, highlightbackground=ENTRY_BORDER,
                     highlightcolor=BLUE, insertbackground=TEXT, validate="key",
                     validatecommand=(self._vcmd, "%P", str(maxlen)))
        e.bind("<FocusIn>", lambda ev: ev.widget.after(1, lambda: ev.widget.select_range(0, "end")))
        e.bind("<FocusOut>", lambda ev, v=var, n=maxlen: self._pad(v, n))
        var.trace_add("write", lambda *a, w=e: self._mark(w, False))
        return e

    @staticmethod
    def _pad(var, maxlen):
        text = var.get()
        if text.isdigit() and maxlen == 2:
            var.set(text.zfill(2))

    def _mark(self, widget, bad):
        if isinstance(widget, ttk.Combobox):
            widget.configure(style="Invalid.TCombobox" if bad else "TCombobox")
        else:
            widget.configure(highlightbackground=INVALID if bad else ENTRY_BORDER,
                             highlightcolor=INVALID if bad else BLUE)

    def _reset_marks(self):
        for w in self._marked:
            try:
                self._mark(w, False)
            except tk.TclError:
                pass
        self._marked = []
        self._status("")

    def _fail(self, err, widgets):
        for w in widgets:
            self._mark(w, True)
            self._marked.append(w)
        self._status(str(err), error=True)
        if widgets:
            widgets[0].focus_set()

    def _status(self, text, error=False):
        self.status.configure(text=text, fg=INVALID if error else MUTED)

    def _link(self, parent, text, command, x, y, anchor="center"):
        l = tk.Label(parent, text=text, bg=PANEL_BG, fg="#111111", font=(FONT, 10, "underline"), cursor="hand2")
        l.bind("<Button-1>", lambda e: command())
        put(l, x, y, anchor=anchor)
        return l

    def _arm(self, key):
        """Grey CALCULATE buttons take the panel colour once the user has changed something."""
        button, colour = self._calc_buttons[key]
        if button._base == GREY:
            recolor(button, colour)

    def _on_enter(self, _event):
        w = self.focus_get()
        if w is None:
            return
        if isinstance(w, tk.Button):
            w.invoke()
            return
        for frame, action in self._panel_actions:
            if str(w).startswith(str(frame) + "."):
                action()
                return

    def _on_wheel(self, event):
        if len(self.rows) <= self.VISIBLE_ROWS:
            return
        target = self.winfo_containing(event.x_root, event.y_root)
        if target is not None and str(target).startswith(str(self.sum_panel) + "."):
            self.rows_canvas.yview_scroll(int(-event.delta / 120), "units")

    # ------------------------------------------------- left: Enter Time panel
    def _build_sum_panel(self):
        p = self.sum_panel = self._panel(22, 24, 180, 606, "Enter Time:", BLUE)
        self._panel_actions.append((p, self._calc_sum))
        for text, cx in (("Hours", 62), ("Minutes", 116)):
            l = tk.Label(p, text=text, bg=PANEL_BG, fg=TEXT, font=self.f_small)
            put(l, cx, 72, anchor="center")
        self.rows_canvas = tk.Canvas(p, bg=PANEL_BG, highlightthickness=0, bd=0, yscrollincrement=px(self.ROW_H))
        put(self.rows_canvas, 0, 88, 176, self.ROW_H * self.VISIBLE_ROWS)
        self.rows_frame = tk.Frame(self.rows_canvas, bg=PANEL_BG)
        self.rows_canvas.create_window((0, 0), window=self.rows_frame, anchor="nw")
        self.rows_frame.bind("<Configure>", lambda e: self.rows_canvas.configure(
            scrollregion=self.rows_canvas.bbox("all")))
        self.rows_scroll = ttk.Scrollbar(p, orient="vertical", command=self.rows_canvas.yview)
        self.rows_canvas.configure(yscrollcommand=self.rows_scroll.set)
        self._add_rows(self.VISIBLE_ROWS)
        self._link(p, "+ Add More Lines", self._add_more_lines, 89, 590)

    def _add_rows(self, n):
        for _ in range(n):
            if len(self.rows) >= self.MAX_ROWS:
                break
            i = len(self.rows)
            f = tk.Frame(self.rows_frame, bg=PANEL_BG, width=px(176), height=px(self.ROW_H))
            f.grid(row=i, column=0)
            hv, mv = tk.StringVar(value="00"), tk.StringVar(value="00")
            he, me = self._box(f, hv, 2), self._box(f, mv, 2)
            put(he, 41, 5, 40, 38)
            put(me, 98, 5, 40, 38)
            colon = tk.Label(f, text=":", bg=PANEL_BG, fg="#111111", font=(FONT, 16, "bold"))
            put(colon, 89, 24, anchor="center")
            he.bind("<KeyRelease>", lambda ev, m=me: self._advance(ev, m, 2, hv))
            me.bind("<KeyRelease>", lambda ev, idx=i: self._advance_row(ev, idx))
            self.rows.append({"h": he, "m": me, "hv": hv, "mv": mv, "frame": f})
        self._update_scrollbar()

    def _advance(self, event, target, n, var):
        if event.char.isdigit() and len(var.get()) >= n:
            target.focus_set()

    def _advance_row(self, event, idx):
        if event.char.isdigit() and len(self.rows[idx]["mv"].get()) >= 2 and idx + 1 < len(self.rows):
            self._scroll_to_row(idx + 1)
            self.rows[idx + 1]["h"].focus_set()

    def _add_more_lines(self):
        self._add_rows(5)
        self.update_idletasks()
        self.rows_canvas.yview_moveto(1.0)

    def _update_scrollbar(self):
        if len(self.rows) > self.VISIBLE_ROWS:
            put(self.rows_scroll, 158, 88, 16, self.ROW_H * self.VISIBLE_ROWS)
        else:
            self.rows_scroll.place_forget()

    def _scroll_to_row(self, i):
        if len(self.rows) > self.VISIBLE_ROWS:
            first = min(max(i - self.VISIBLE_ROWS + 2, 0), len(self.rows) - self.VISIBLE_ROWS)
            self.rows_canvas.yview_moveto(first / len(self.rows))

    # ------------------------------------------------ middle: See Your Total
    def _build_total_panel(self):
        p = self.total_panel = self._panel(236, 24, 180, 603, "See Your Total:", BLUE)
        self.total_h, self.total_m = tk.StringVar(value="00"), tk.StringVar(value="00")
        self.total_dec = tk.StringVar(value="0.00")
        for var, x in ((self.total_h, 41), (self.total_m, 97)):
            l = tk.Label(p, textvariable=var, bg=GREY, fg="white", font=self.f_entry)
            put(l, x, 91, 40, 38)
        put(tk.Label(p, text=":", bg=PANEL_BG, fg="#111111", font=(FONT, 16, "bold")), 90, 110, anchor="center")
        l = tk.Label(p, textvariable=self.total_dec, bg=GREY, fg="white", font=self.f_entry)
        put(l, 26, 175, 125, 37)
        for text, cmd, y in (("CALCULATE", self._calc_sum, 247), ("CLEAR", self._clear_sum, 324),
                             ("PRINT", self._print, 401), ("EMAIL", self._email, 478)):
            put(make_button(p, text, cmd, BLUE, font=self.f_btn), 26, y, 125, 42)

    def _calc_sum(self):
        self._reset_marks()
        try:
            minutes = core.parse_rows([(r["hv"].get(), r["mv"].get()) for r in self.rows])
        except core.ValidationError as err:
            i, key = err.field
            self._scroll_to_row(i)
            self._fail(err, [self.rows[i][key]])
            return None
        total = sum(minutes)
        h, m = core.split_hm(total)
        self.total_h.set(f"{h:02d}")
        self.total_m.set(f"{m:02d}")
        self.total_dec.set(core.format_decimal(total))
        used = sum(1 for x in minutes if x)
        self._status(f"Added {core.plural(used, 'line')}: {h:02d}:{m:02d} = {core.format_decimal(total)} hours.")
        return minutes

    def _clear_sum(self):
        self._reset_marks()
        for extra in self.rows[self.VISIBLE_ROWS:]:
            extra["frame"].destroy()
        del self.rows[self.VISIBLE_ROWS:]
        for r in self.rows:
            r["hv"].set("00")
            r["mv"].set("00")
        self.total_h.set("00")
        self.total_m.set("00")
        self.total_dec.set("0.00")
        self.rows_canvas.yview_moveto(0)
        self._update_scrollbar()
        self.rows[0]["h"].focus_set()

    def _print(self):
        minutes = self._calc_sum()
        if minutes is None:
            return
        try:
            mailer.print_text(mailer.time_report(minutes))
            self._status("Sent to the default printer.")
        except Exception as exc:
            messagebox.showerror("Print", f"The total could not be printed:\n{exc}", parent=self)

    def _email(self):
        minutes = self._calc_sum()
        if minutes is None:
            return
        total = sum(minutes)
        h, m = core.split_hm(total)
        subject = f"Time total: {h:02d}:{m:02d} ({core.format_decimal(total)} hours)"
        body = mailer.time_report(minutes)
        try:
            how = mailer.open_email_draft(subject, body)
            self._status("Draft opened in Outlook." if how == "outlook" else "Draft opened in your default e-mail app.")
        except Exception as exc:
            self.clipboard_clear()
            self.clipboard_append(body)
            messagebox.showerror("Email", f"No e-mail draft could be opened ({exc}).\n"
                                          "The report was copied to the clipboard instead.", parent=self)

    # --------------------------------------------- right-top: Time Between Hours
    def _build_hours_panel(self):
        p = self.hours_panel = self._panel(447, 24, 317, 283, "Time Between Hours", RED, anchor="w")
        self._panel_actions.append((p, self._calc_hours))
        self.hours_vars, self.hours_widgets = {}, {}
        for prefix, label, cy in (("from", "From:", 79), ("to", "To:", 126)):
            put(tk.Label(p, text=label, bg=PANEL_BG, fg=TEXT, font=self.f_body), 16, cy, anchor="w")
            hv, mv, ap = tk.StringVar(value="00"), tk.StringVar(value="00"), tk.StringVar(value="AM")
            he, me = self._box(p, hv, 2), self._box(p, mv, 2)
            put(he, 79, cy - 19, 40, 38)
            put(me, 139, cy - 19, 40, 38)
            put(tk.Label(p, text=":", bg=PANEL_BG, fg="#111111", font=(FONT, 14, "bold")), 129, cy - 2, anchor="center")
            he.bind("<KeyRelease>", lambda ev, t=me, v=hv: self._advance(ev, t, 2, v))
            self._ampm(p, ap, 194, cy - 19)
            for var in (hv, mv, ap):
                var.trace_add("write", lambda *a: self._arm("hours"))
            self.hours_vars[prefix] = (hv, mv, ap)
            self.hours_widgets[prefix] = {"h": he, "m": me}
        btn = make_button(p, "CALCULATE", self._calc_hours, GREY, font=self.f_btn)
        put(btn, 80, 154, 212, 42)
        self._calc_buttons["hours"] = (btn, RED)
        put(tk.Label(p, text="Total:", bg=PANEL_BG, fg=TEXT, font=self.f_body), 16, 223, anchor="w")
        self.hours_total = tk.StringVar(value="00.00")
        put(self._result_entry(p, self.hours_total), 81, 205, 210, 38)
        self._link(p, "Clear", self._clear_hours, 85, 262)
        self._link(p, "More Options", self._hours_options, 242, 262)

    def _result_entry(self, parent, var):
        return tk.Entry(parent, textvariable=var, state="readonly", justify="center", font=self.f_entry,
                        readonlybackground="white", fg=TEXT, relief="flat", bd=0, highlightthickness=1,
                        highlightbackground=ENTRY_BORDER, highlightcolor=ENTRY_BORDER)

    def _ampm(self, parent, var, x, y):
        buttons = {}

        def refresh(*_):
            for name, b in buttons.items():
                on = var.get() == name
                recolor(b, GREY if on else "#EEEEEE", "white" if on else "#444444")

        for name, bx in (("AM", x), ("PM", x + 50)):
            b = make_button(parent, name, lambda n=name: var.set(n), "#EEEEEE", "#444444", font=self.f_small)
            put(b, bx, y, 42, 38)
            buttons[name] = b
        var.trace_add("write", refresh)
        refresh()

    def _calc_hours(self):
        self._reset_marks()
        opts = self.settings.hours
        try:
            mins = []
            for prefix, label in (("from", "Start"), ("to", "End")):
                hv, mv, ap = self.hours_vars[prefix]
                mins.append(core.to_minute_of_day(hv.get(), mv.get(), ap.get(), label, prefix))
            result = core.time_between(mins[0], mins[1], opts)
        except core.ValidationError as err:
            f = err.field
            widgets = list(self.hours_widgets[f[0]].values()) if len(f) == 1 else [self.hours_widgets[f[0]][f[1]]]
            self._fail(err, widgets)
            return
        self.hours_total.set(core.format_hours_result(result, opts.output))
        h, m = core.split_hm(result)
        note = f", after a {opts.break_minutes}-minute break" if opts.break_minutes else ""
        self._status(f"{core.format_clock(mins[0])} to {core.format_clock(mins[1])} = {h} h {m} min "
                     f"({core.format_decimal(result)} hours){note}.")

    def _clear_hours(self):
        self._reset_marks()
        for hv, mv, ap in self.hours_vars.values():
            hv.set("00")
            mv.set("00")
            ap.set("AM")
        self.hours_total.set("00.00")
        recolor(self._calc_buttons["hours"][0], GREY)

    def _hours_options(self):
        def save(opts):
            self.settings.hours = opts
            settings_store.save(self.settings)
            self._status("Options saved. Press CALCULATE to apply them.")
        HoursOptionsDialog(self, self.settings.hours, save)

    # -------------------------------------------- right-bottom: Time Between Dates
    def _build_dates_panel(self):
        p = self.dates_panel = self._panel(447, 343, 317, 303, "Time Between Dates", GREEN, anchor="w")
        self._panel_actions.append((p, self._calc_dates))
        self.date_vars, self.date_widgets = {}, {}
        today = dt.date.today()
        defaults = {"from": today, "to": core.add_months(today, 1)}
        for prefix, label, cy in (("from", "From:", 79), ("to", "To:", 126)):
            put(tk.Label(p, text=label, bg=PANEL_BG, fg=TEXT, font=self.f_body), 16, cy, anchor="w")
            d = defaults[prefix]
            mv, dv, yv = tk.StringVar(value=MONTHS[d.month - 1]), tk.StringVar(value=str(d.day)), tk.StringVar(value=str(d.year))
            cm = ttk.Combobox(p, textvariable=mv, values=MONTHS, state="readonly", font=self.f_body)
            cd = ttk.Combobox(p, textvariable=dv, values=[str(i) for i in range(1, 32)], state="readonly", font=self.f_body)
            ye = self._box(p, yv, 4)
            put(cm, 79, cy - 19, 58, 38)
            put(cd, 144, cy - 19, 58, 38)
            put(ye, 210, cy - 19, 64, 38)
            for cb in (cm, cd):
                cb.bind("<<ComboboxSelected>>", lambda ev: (self._mark(ev.widget, False), self._arm("dates")))
            yv.trace_add("write", lambda *a: self._arm("dates"))
            icon = self._calendar_icon(p, lambda pr=prefix: self._open_calendar(pr))
            put(icon, 281, cy - 15, 30, 30)
            self.date_vars[prefix] = {"m": mv, "d": dv, "y": yv}
            self.date_widgets[prefix] = {"m": cm, "d": cd, "y": ye, "icon": icon}
        btn = make_button(p, "CALCULATE", self._calc_dates, GREY, font=self.f_btn)
        put(btn, 80, 154, 212, 42)
        self._calc_buttons["dates"] = (btn, GREEN)
        put(tk.Label(p, text="Total:", bg=PANEL_BG, fg=TEXT, font=self.f_body), 16, 244, anchor="w")
        self.dates_total = tk.StringVar(value="00.00")
        put(self._result_entry(p, self.dates_total), 81, 225, 210, 38)
        self._link(p, "Clear", self._clear_dates, 85, 282)
        self._link(p, "More Options", self._dates_options, 242, 282)

    def _calendar_icon(self, parent, command):
        c = tk.Canvas(parent, width=px(30), height=px(30), bg=PANEL_BG, highlightthickness=0, cursor="hand2")
        k = px
        c.create_rectangle(k(3), k(6), k(27), k(27), fill="#E4E4E4", outline="#8A8A8A", width=1)
        c.create_rectangle(k(3), k(6), k(27), k(11), fill="#8A8A8A", outline="#8A8A8A")
        for x in (8, 20):
            c.create_rectangle(k(x), k(2), k(x + 2), k(8), fill="#6F6F6F", outline="")
        for r in range(3):
            for col in range(4):
                c.create_rectangle(k(6 + col * 5), k(13 + r * 4.5), k(9.5 + col * 5), k(16 + r * 4.5),
                                   fill="#9A9A9A", outline="")
        c.bind("<Button-1>", lambda e: command())
        return c

    def _read_date(self, prefix, label):
        v = self.date_vars[prefix]
        name = v["m"].get()
        if name not in MONTHS:
            raise core.ValidationError(f"{label}: choose a month.", (prefix, "m"))
        return core.make_date(MONTHS.index(name) + 1, v["d"].get(), v["y"].get(), label, prefix)

    def _open_calendar(self, prefix):
        try:
            initial = self._read_date(prefix, "Date")
        except core.ValidationError:
            initial = dt.date.today()

        def pick(d):
            v = self.date_vars[prefix]
            v["m"].set(MONTHS[d.month - 1])
            v["d"].set(str(d.day))
            v["y"].set(str(d.year))
        CalendarPopup(self, self.date_widgets[prefix]["icon"], initial, pick)

    def _calc_dates(self):
        self._reset_marks()
        opts = self.settings.dates
        try:
            start = self._read_date("from", "Start")
            end = self._read_date("to", "End")
            res = core.date_difference(start, end, opts)
        except core.ValidationError as err:
            f = err.field
            widgets = ([w for k, w in self.date_widgets[f[0]].items() if k != "icon"]
                       if len(f) == 1 else [self.date_widgets[f[0]][f[1]]])
            self._fail(err, widgets)
            return
        self.dates_total.set(core.format_date_result(res, opts))
        extra = ""
        if opts.mode == "working":
            extra = (f" ({res.calendar_days} calendar days; skipped {res.weekend_skipped} weekend day(s)"
                     f" and {res.holidays_skipped} holiday(s))")
        self._status(f"{start:%d %b %Y} to {end:%d %b %Y}: {core.format_date_result(res, opts)}. "
                     f"Rules: {core.describe_rules(opts)}.{extra}")

    def _clear_dates(self):
        self._reset_marks()
        today = dt.date.today()
        for prefix, d in (("from", today), ("to", core.add_months(today, 1))):
            v = self.date_vars[prefix]
            v["m"].set(MONTHS[d.month - 1])
            v["d"].set(str(d.day))
            v["y"].set(str(d.year))
        self.dates_total.set("00.00")
        recolor(self._calc_buttons["dates"][0], GREY)

    def _dates_options(self):
        def save(opts):
            self.settings.dates = opts
            settings_store.save(self.settings)
            self._status("Options saved. Press CALCULATE to apply them.")
        DateOptionsDialog(self, self.settings.dates, save)


def run():
    TimeCalculatorApp().mainloop()
