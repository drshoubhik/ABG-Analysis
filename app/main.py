"""
ABG Analyser - Kivy GUI (dark, single scrollable screen).
Drives abg_core.analyse(); no clinical logic lives in this file.
Author: Dr. Shoubhik Banerjee
"""

from kivy.app import App
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.togglebutton import ToggleButton
from kivy.utils import get_color_from_hex

from abg_core import Inputs, analyse, causes_for

PAL = {
    "bg": "#0D1117", "surface": "#161B22", "surface2": "#21262D",
    "accent": "#00B4D8", "text": "#E6EDF3", "dim": "#8B949E",
    "muted": "#484F58", "danger": "#FF4D4D", "warning": "#FFB347",
    "success": "#3DD68C", "btn": "#003566", "yes": "#1A4731", "no": "#4A1C1C",
}


def col(k):
    return get_color_from_hex(PAL[k])


def para(text, **kw):
    """Wrapping label whose height follows its text."""
    kw.setdefault("halign", "left")
    lbl = Label(text=text, size_hint_y=None, valign="middle", **kw)
    lbl.bind(width=lambda w, wd: setattr(w, "text_size", (wd, None)),
             texture_size=lambda w, ts: setattr(w, "height", ts[1] + dp(6)))
    return lbl


class Card(BoxLayout):
    def __init__(self, title, **kw):
        super().__init__(orientation="vertical", size_hint_y=None,
                         padding=dp(12), spacing=dp(6), **kw)
        self.bind(minimum_height=self.setter("height"))
        with self.canvas.before:
            Color(*col("surface"))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])
        self.bind(pos=self._sync, size=self._sync)
        self.add_widget(para(title, color=col("accent"), bold=True, font_size=dp(13)))

    def _sync(self, *a):
        self._bg.pos, self._bg.size = self.pos, self.size


class Field(BoxLayout):
    def __init__(self, label, hint, unit="", **kw):
        super().__init__(size_hint_y=None, height=dp(46), spacing=dp(6), **kw)
        lbl = Label(text=label, color=col("text"), font_size=dp(13), size_hint_x=0.34,
                    halign="left", valign="middle")
        lbl.bind(size=lambda w, s: setattr(w, "text_size", s))   # vertically centred in the row
        self.add_widget(lbl)
        self.inp = TextInput(
            hint_text=hint, multiline=False, input_filter="float",
            background_color=col("surface2"), foreground_color=col("text"),
            hint_text_color=col("muted"), cursor_color=col("accent"),
            font_size=dp(15), padding=[dp(10), dp(11)])
        self.add_widget(self.inp)
        u = Label(text=unit, color=col("dim"), font_size=dp(11), size_hint_x=0.24,
                  halign="left", valign="middle")
        u.bind(size=lambda w, s: setattr(w, "text_size", s))
        self.add_widget(u)

    @property
    def text(self):
        return self.inp.text.strip()


def row(key, value, value_color=None):
    r = BoxLayout(size_hint_y=None, spacing=dp(8))
    r.bind(minimum_height=r.setter("height"))
    r.add_widget(para(key, color=col("dim"), font_size=dp(12), size_hint_x=0.46))
    r.add_widget(para(str(value), color=value_color or col("text"), bold=True,
                      font_size=dp(13), size_hint_x=0.54, halign="right"))
    return r


def choice_popup(title, text, options, callback=None):
    """Modal with a row of buttons. options = [(label, value), ...]."""
    box = BoxLayout(orientation="vertical", padding=dp(14), spacing=dp(12))
    box.add_widget(para(text, color=col("text"), font_size=dp(14)))
    btns = BoxLayout(spacing=dp(10), size_hint_y=None, height=dp(48))
    pop = Popup(title=title, title_color=col("accent"), content=box,
                size_hint=(0.9, 0.5), background_color=col("surface"),
                separator_color=col("accent"))
    for label, value in options:
        b = Button(text=label, background_color=col("btn"), color=col("text"), bold=True)

        def pick(_b, v=value):
            pop.dismiss()
            if callback is not None:
                callback(v)
        b.bind(on_release=pick)
        btns.add_widget(b)
    box.add_widget(btns)
    pop.open()


def parse_num(field, lo, hi, name, optional=False):
    """Returns (value, error). Blank + optional -> (None, None)."""
    t = field.text
    if not t:
        return (None, None) if optional else (None, f"{name}: required")
    try:
        v = float(t)
    except ValueError:
        return None, f"{name}: not a number"
    if not lo <= v <= hi:
        return None, f"{name}: must be between {lo} and {hi}"
    return v, None


class ABGScreen(ScrollView):
    def __init__(self, **kw):
        super().__init__(do_scroll_x=False, **kw)
        self._answers = {}      # answers to resp_primary / acuity for the current core values
        self._key = None
        self.selected_causes = set()

        self.root_box = BoxLayout(orientation="vertical", padding=dp(12), spacing=dp(12),
                                  size_hint_y=None)
        self.root_box.bind(minimum_height=self.root_box.setter("height"))
        with self.canvas.before:
            Color(*col("bg"))
            self._bg = RoundedRectangle(pos=self.pos, size=self.size, radius=[0])
        self.bind(pos=self._sync_bg, size=self._sync_bg)

        head = Label(text="ABG ANALYSER", color=col("accent"), bold=True,
                     font_size=dp(22), size_hint_y=None, height=dp(36))
        sub = Label(text="Dr. Shoubhik Banerjee  |  ICU reference", color=col("dim"),
                    font_size=dp(11), size_hint_y=None, height=dp(18))
        self.root_box.add_widget(head)
        self.root_box.add_widget(sub)

        # ABG card
        abg = Card("ARTERIAL BLOOD GAS")
        self.f_ph = Field("pH", "7.35 - 7.45")
        self.f_pco2 = Field("pCO2", "35 - 45", "mmHg")
        self.f_hco3 = Field("HCO3", "22 - 26", "mEq/L")
        self.f_po2 = Field("pO2", "optional", "mmHg")
        self.f_fio2 = Field("FiO2", "21-100 (with pO2)", "%")
        self.f_age = Field("Age", "optional", "years")
        for f in (self.f_ph, self.f_pco2, self.f_hco3, self.f_po2, self.f_fio2, self.f_age):
            abg.add_widget(f)
        self.root_box.add_widget(abg)

        # Electrolytes card: only revealed when a metabolic acidosis needs classifying
        self.elec_card = Card("ELECTROLYTES  (metabolic acidosis)")
        self.f_na = Field("Na+", "135 - 145", "mEq/L")
        self.f_cl = Field("Cl-", "95 - 105", "mEq/L")
        self.f_alb = Field("Albumin", "optional", "g/dL")
        for f in (self.f_na, self.f_cl, self.f_alb):
            self.elec_card.add_widget(f)
        self.elec_slot = BoxLayout(orientation="vertical", size_hint_y=None)
        self.elec_slot.bind(minimum_height=self.elec_slot.setter("height"))
        self.root_box.add_widget(self.elec_slot)

        btn_row = BoxLayout(size_hint_y=None, height=dp(50), spacing=dp(10))
        analyse_btn = Button(text="ANALYSE ABG", background_color=col("btn"),
                             color=col("text"), bold=True, size_hint_x=0.65)
        analyse_btn.bind(on_release=self.on_analyse)
        new_btn = Button(text="NEW ABG", background_color=col("surface2"),
                         color=col("dim"), bold=True, size_hint_x=0.35)
        new_btn.bind(on_release=self.on_new)
        btn_row.add_widget(analyse_btn)
        btn_row.add_widget(new_btn)
        self.root_box.add_widget(btn_row)

        # Results and causes are rebuilt on each analysis
        self.results_slot = BoxLayout(orientation="vertical", size_hint_y=None, spacing=dp(12))
        self.results_slot.bind(minimum_height=self.results_slot.setter("height"))
        self.root_box.add_widget(self.results_slot)

        self.root_box.add_widget(para(
            "Decision support only. Always interpret with the clinical picture.",
            color=col("muted"), font_size=dp(10), halign="center"))

        self.add_widget(self.root_box)

    def _sync_bg(self, *a):
        self._bg.pos, self._bg.size = self.pos, self.size

    # ── input handling ───────────────────────────────────────────
    def on_new(self, *_):
        """Clear everything, including electrolytes, so nothing carries over to the next patient."""
        for f in (self.f_ph, self.f_pco2, self.f_hco3, self.f_po2, self.f_fio2, self.f_age,
                  self.f_na, self.f_cl, self.f_alb):
            f.inp.text = ""
        if self.elec_card.parent is not None:
            self.elec_slot.remove_widget(self.elec_card)
        self.results_slot.clear_widgets()
        self._answers, self._key = {}, None
        self.selected_causes = set()
        self.scroll_y = 1

    def on_analyse(self, *_):
        errs = []

        def g(field, lo, hi, name, opt=False):
            v, e = parse_num(field, lo, hi, name, opt)
            if e:
                errs.append(e)
            return v

        ph = g(self.f_ph, 6.5, 7.8, "pH")
        pco2 = g(self.f_pco2, 5, 150, "pCO2")
        hco3 = g(self.f_hco3, 2, 60, "HCO3")
        pao2 = g(self.f_po2, 1, 700, "pO2", opt=True)
        fio2 = g(self.f_fio2, 21, 100, "FiO2") if pao2 is not None else None
        age = g(self.f_age, 0, 120, "Age", opt=True)
        na = g(self.f_na, 100, 180, "Na", opt=True)
        cl = g(self.f_cl, 70, 140, "Cl") if na is not None else None   # required with Na, as v2.0
        alb = g(self.f_alb, 0.5, 6.0, "Albumin", opt=True) if na is not None else None

        if errs:
            return choice_popup("Input error", "\n".join(errs), [("OK", None)])

        key = (ph, pco2, hco3)
        if key != self._key:           # new ABG: forget old answers
            self._answers, self._key = {}, key

        self.inp = Inputs(
            ph=ph, pco2=pco2, hco3=hco3, pao2=pao2,
            fio2=fio2 / 100 if fio2 is not None else None,
            na=na, cl=cl, albumin=alb, age=age,
            resp_primary=self._answers.get("resp_primary"),
            acuity=self._answers.get("acuity"),
        )
        self._run()

    def _run(self):
        res = analyse(self.inp)

        if res.status == "invalid":
            # Hard stop: no interpretation of an internally inconsistent gas
            self.results_slot.clear_widgets()
            return choice_popup("ABG not valid", "\n".join(res.notes), [("Re-enter", None)])

        if res.status == "needs_input":
            need = res.needs[0]
            if need == "resp_primary":
                sug = "Respiratory" if res.suggested_resp_primary else "Metabolic"
                return choice_popup(
                    "Which is primary?",
                    f"pH {self.inp.ph} ({res.ph_status}): the gas alone can't decide.\n"
                    f"From the clinical history, which is the PRIMARY disorder?\n"
                    f"(pH suggests: {sug})",
                    [("Respiratory", True), ("Metabolic", False)],
                    self._answer("resp_primary"))
            if need == "acuity":
                return choice_popup(
                    "Acute or chronic?",
                    f"Is the respiratory disorder acute or chronic?\n"
                    f"HCO3 fits {res.suggested_acuity}.",
                    [("Acute", "acute"), ("Chronic", "chronic")],
                    self._answer("acuity"))
            if need == "electrolytes":
                # reveal the electrolyte card; user fills it and presses Analyse again
                if self.elec_card.parent is None:
                    self.elec_slot.add_widget(self.elec_card)
                self.results_slot.clear_widgets()
                return choice_popup(
                    "Electrolytes needed",
                    "A metabolic acidosis needs classifying (anion gap or not). "
                    "Enter Na and Cl in the Electrolytes card, then press ANALYSE again.",
                    [("OK", None)])

        self._render(res)

    def _answer(self, name):
        def cb(value):
            self._answers[name] = value
            setattr(self.inp, name, value)      # name is an Inputs field
            self._run()
        return cb

    # ── rendering ────────────────────────────────────────────────
    def _render(self, r):
        self.results_slot.clear_widgets()
        self.selected_causes = set()

        d = Card("DIAGNOSIS")
        d.add_widget(para(f"pH {self.inp.ph}  ->  {r.ph_status}", color=col("dim"),
                          font_size=dp(12)))
        h = r.headline.lower()
        if r.headline == "Normal acid-base status":
            hc = col("success")
        elif "acidosis" in h or r.concurrent:
            hc = col("danger")
        else:
            hc = col("warning")
        d.add_widget(para(r.headline, bold=True, font_size=dp(16), color=hc))
        if r.hh_consistent:
            d.add_widget(para(f"HH check: consistent (expected HCO3 ≈ {r.hh_expected_hco3})",
                              color=col("success"), font_size=dp(11)))
        self.results_slot.add_widget(d)

        if r.compensation:
            c = r.compensation
            comp = Card("COMPENSATION")
            comp.add_widget(row(f"Expected {c['param']}", f"{c['expected']} ({c['low']}-{c['high']})"))
            comp.add_widget(row(f"Measured {c['param']}", c["actual"]))
            comp.add_widget(row("Verdict", c["verdict"],
                                col("success") if c["verdict"] == "Appropriate" else col("warning")))
            comp.add_widget(para(c["formula"], color=col("muted"), font_size=dp(10)))
            self.results_slot.add_widget(comp)

        if r.ag_raw is not None:
            ag = Card("ANION GAP")
            ag.add_widget(row("AG (raw)", f"{r.ag_raw:.1f} mEq/L"))
            if r.ag_albumin_corrected:
                ag.add_widget(row("AG (albumin-corrected)", f"{r.ag_corrected:.1f} mEq/L"))
            else:
                ag.add_widget(para("Albumin not entered: AG not corrected",
                                   color=col("muted"), font_size=dp(10)))
            ag.add_widget(row("Status", "Raised (>12)" if r.ag_elevated else "Normal (<=12)",
                              col("danger") if r.ag_elevated else col("success")))
            if r.corrected_hco3 is not None:
                flagged = r.second_process.startswith("Consider")
                ag.add_widget(row("Corrected HCO3", f"{r.corrected_hco3}  (HCO3 + AG excess)"))
                ag.add_widget(para(r.second_process, font_size=dp(12),
                                   color=col("warning") if flagged else col("dim")))
            self.results_slot.add_widget(ag)

        if r.pf_ratio is not None:
            o = Card("OXYGENATION")
            o.add_widget(row("Hypoxemia", r.hypoxemia,
                             col("danger") if "Severe" in r.hypoxemia else
                             col("warning") if "hypoxemia" in r.hypoxemia.lower()
                             and "No" not in r.hypoxemia else col("success")))
            o.add_widget(row("P/F ratio", f"{r.pf_ratio}  ({r.pf_grade})"))
            aa = f"{r.aa_gradient} mmHg"
            if r.aa_expected is not None:
                state = "raised" if r.aa_gradient > r.aa_expected else "normal"
                aa += f"  ({state}; expected <= {r.aa_expected})"
            else:
                aa += "  (age not entered: not assessed)"
            o.add_widget(row("A-a gradient", aa))
            if r.pf_ratio <= 300:
                o.add_widget(para("Note: ARDS also needs acute onset, bilateral opacities, PEEP ≥ 5.",
                                  color=col("muted"), font_size=dp(10)))
            self.results_slot.add_widget(o)

        for n in r.notes:
            self.results_slot.add_widget(para(f"! {n}", color=col("warning"), font_size=dp(12)))

        self._render_causes(causes_for(r))

    def _render_causes(self, causes):
        if not causes:
            return
        card = Card("PROBABLE CAUSES: tap Yes / No")
        self.sel_label = para("", color=col("accent"), font_size=dp(12))
        for cause in causes:
            line = BoxLayout(size_hint_y=None, spacing=dp(6))
            line.bind(minimum_height=line.setter("height"))
            line.add_widget(para(cause, color=col("text"), font_size=dp(12), size_hint_x=0.6))
            grp = f"cause::{cause}"
            # flat backgrounds (background_normal/down = "") so the colours show exactly
            flat = dict(group=grp, allow_no_selection=False, size_hint_x=0.2, size_hint_y=None,
                        height=dp(36), background_normal="", background_down="", bold=True)
            yes = ToggleButton(text="Yes", **flat)
            no = ToggleButton(text="No", state="down", **flat)

            def paint(_btn=None, _state=None, c=cause, y=yes, n=no):
                on = y.state == "down"
                y.background_color = col("success") if on else col("surface2")
                y.color = col("bg") if on else col("muted")
                n.background_color = col("surface2") if on else col("muted")
                n.color = col("muted") if on else col("text")
                self._toggle(c, on)
            paint()
            yes.bind(state=paint)
            line.add_widget(yes)
            line.add_widget(no)
            card.add_widget(line)
        card.add_widget(self.sel_label)
        self.results_slot.add_widget(card)

    def _toggle(self, cause, on):
        (self.selected_causes.add if on else self.selected_causes.discard)(cause)
        self.sel_label.text = ("Selected: " + ", ".join(sorted(self.selected_causes))
                               if self.selected_causes else "")


class ABGApp(App):
    def build(self):
        Window.clearcolor = col("bg")
        self.title = "ABG Analyser"
        return ABGScreen()


if __name__ == "__main__":
    ABGApp().run()
