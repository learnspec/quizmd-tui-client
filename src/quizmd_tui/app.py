"""QuizMD TUI — main Textual application."""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import httpx
from pylearnspec import parse_quiz
from pylearnspec.quizmd.models import Choice, Question, Quiz
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.css.query import NoMatches
from textual.reactive import reactive
from textual.screen import ModalScreen, Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Markdown,
    ProgressBar,
    Static,
)

from .github import QuizSource, fetch_file, list_quiz_files, parse_source

# ─── Styles ──────────────────────────────────────────────────────────────────

CSS = """\
Screen {
    background: $surface;
}

/* ── Welcome screen ──────────────────────────────────────────────── */
#welcome {
    align: center middle;
    width: 100%;
    height: 100%;
}
#welcome-box {
    width: 72;
    height: auto;
    max-height: 80%;
    padding: 2 4;
    border: round $primary;
    background: $panel;
}
#welcome-box #logo {
    text-align: center;
    color: $text;
    text-style: bold;
    margin-bottom: 1;
}
#welcome-box #tagline {
    text-align: center;
    color: $text-muted;
    margin-bottom: 2;
}
#welcome-box Input {
    margin-bottom: 1;
}
#welcome-box Button {
    width: 100%;
    margin-top: 1;
}
#error-label {
    color: $error;
    text-align: center;
    margin-top: 1;
    display: none;
}
#error-label.visible {
    display: block;
}

/* ── File picker ─────────────────────────────────────────────────── */
#picker {
    align: center middle;
    width: 100%;
    height: 100%;
}
#picker-box {
    width: 72;
    height: auto;
    max-height: 85%;
    padding: 2 4;
    border: round $primary;
    background: $panel;
}
#picker-box #picker-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}
#picker-box ListView {
    height: auto;
    max-height: 20;
    margin-bottom: 1;
}
#picker-box ListItem {
    padding: 0 2;
}
#picker-box ListItem:hover {
    background: $accent 20%;
}

/* ── Quiz screen ─────────────────────────────────────────────────── */
#quiz-header {
    dock: top;
    height: 3;
    padding: 0 2;
    background: $primary;
    color: $text;
}
#quiz-header #quiz-title {
    text-style: bold;
}
#quiz-header #quiz-progress {
    dock: right;
    width: auto;
}

#question-area {
    width: 100%;
    height: 1fr;
    padding: 1 2;
}
#question-area #q-number {
    color: $accent;
    text-style: bold;
    margin-bottom: 1;
}
#question-area #q-body {
    margin-bottom: 1;
}
#question-area #q-hint {
    color: $warning;
    margin-bottom: 1;
    display: none;
}
#question-area #q-hint.visible {
    display: block;
}

/* choices */
.choice-btn {
    width: 100%;
    margin-bottom: 0;
    min-height: 1;
    height: auto;
    content-align: left middle;
}
.choice-btn.selected {
    background: $accent 30%;
    border-left: thick $accent;
}
.choice-btn.correct-reveal {
    background: $success 30%;
    border-left: thick $success;
}
.choice-btn.wrong-reveal {
    background: $error 20%;
    border-left: thick $error;
}

#choice-feedback {
    color: $text-muted;
    margin-top: 0;
    margin-left: 4;
    display: none;
}
#choice-feedback.visible {
    display: block;
}

/* open answer */
#open-input {
    margin-bottom: 1;
}

/* feedback area */
#feedback-area {
    margin-top: 1;
    padding: 1 2;
    display: none;
}
#feedback-area.visible {
    display: block;
}
#feedback-correct {
    color: $success;
    text-style: bold;
}
#feedback-wrong {
    color: $error;
    text-style: bold;
}
#feedback-text {
    color: $text-muted;
    margin-top: 0;
}

/* nav */
#nav-bar {
    dock: bottom;
    height: 3;
    padding: 0 2;
    align: right middle;
}
#nav-bar Button {
    margin-left: 1;
}

/* ── Results screen ──────────────────────────────────────────────── */
#results {
    align: center middle;
    width: 100%;
    height: 100%;
}
#results-box {
    width: 64;
    height: auto;
    max-height: 85%;
    padding: 2 4;
    border: round $primary;
    background: $panel;
}
#results-box #results-title {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}
#results-box #score-display {
    text-align: center;
    text-style: bold;
    margin-bottom: 1;
}
#results-box #pass-fail {
    text-align: center;
    margin-bottom: 1;
}
#results-box #pass-fail.pass {
    color: $success;
    text-style: bold;
}
#results-box #pass-fail.fail {
    color: $error;
    text-style: bold;
}
#results-box ProgressBar {
    margin: 1 0;
}
#results-box #breakdown-title {
    text-style: bold;
    margin-top: 1;
    margin-bottom: 0;
}
#results-box .result-line {
    margin-left: 2;
}
#results-box .result-correct {
    color: $success;
}
#results-box .result-wrong {
    color: $error;
}
#results-box .result-skip {
    color: $warning;
}
#results-box Button {
    width: 100%;
    margin-top: 2;
}
"""


# ─── Data helpers ────────────────────────────────────────────────────────────

@dataclass
class AnswerRecord:
    question_number: int
    correct: bool
    skipped: bool = False
    points_earned: float = 0.0
    points_possible: float = 1.0


# ─── Welcome Screen ─────────────────────────────────────────────────────────

class WelcomeScreen(Screen):
    BINDINGS = [Binding("escape", "quit", "Quit")]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="welcome"):
            with Vertical(id="welcome-box"):
                yield Static(
                    "┌──────────────────────────────┐\n"
                    "│      ╔═╗ ╦ ╦ ╦ ╔═╗ ╔╦╗ ╔╦╗  │\n"
                    "│      ║ ║ ║ ║ ║ ╔═╝ ║║║  ║║   │\n"
                    "│      ╚═╝ ╚═╝ ╩ ╚═╝ ╩ ╩ ═╩╝  │\n"
                    "│             T U I              │\n"
                    "└──────────────────────────────┘",
                    id="logo",
                )
                yield Static(
                    "Play QuizMD files from GitHub — right in your terminal",
                    id="tagline",
                )
                yield Input(
                    placeholder="owner/repo  or  GitHub URL to a .quiz.md file",
                    id="source-input",
                )
                yield Button("▶  Play", variant="primary", id="play-btn")
                yield Label("", id="error-label")
        yield Footer()

    @on(Button.Pressed, "#play-btn")
    def handle_play(self) -> None:
        self._start_load()

    @on(Input.Submitted, "#source-input")
    def handle_submit(self) -> None:
        self._start_load()

    def _start_load(self) -> None:
        inp = self.query_one("#source-input", Input)
        raw = inp.value.strip()
        if not raw:
            self._show_error("Please enter a GitHub source")
            return
        try:
            source = parse_source(raw)
        except ValueError as exc:
            self._show_error(str(exc))
            return
        self._show_error("")
        self.app.push_screen(LoadingScreen(source))

    def _show_error(self, msg: str) -> None:
        lbl = self.query_one("#error-label", Label)
        lbl.update(msg)
        if msg:
            lbl.add_class("visible")
        else:
            lbl.remove_class("visible")


# ─── Loading Screen ─────────────────────────────────────────────────────────

class LoadingScreen(Screen):
    def __init__(self, source: QuizSource) -> None:
        super().__init__()
        self.source = source

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="welcome"):
            with Vertical(id="welcome-box"):
                yield Static(
                    f"⏳  Fetching from {self.source.display_name}…",
                    id="loading-msg",
                )
        yield Footer()

    def on_mount(self) -> None:
        self.load_quiz()

    @work(exclusive=True)
    async def load_quiz(self) -> None:
        source = self.source
        async with httpx.AsyncClient(
            follow_redirects=True, timeout=30.0
        ) as client:
            try:
                if source.path and source.path.endswith(".quiz.md"):
                    content = await fetch_file(client, source)
                    quiz = parse_quiz(content)
                    self.app.pop_screen()
                    self.app.push_screen(QuizScreen(quiz))
                else:
                    files = await list_quiz_files(client, source)
                    if not files:
                        self.app.pop_screen()
                        self.app.push_screen(WelcomeScreen())
                        self.app.notify(
                            "No .quiz.md files found in this repo",
                            severity="error",
                        )
                        return
                    if len(files) == 1:
                        source.path = files[0].path
                        content = await fetch_file(client, source)
                        quiz = parse_quiz(content)
                        self.app.pop_screen()
                        self.app.push_screen(QuizScreen(quiz))
                    else:
                        self.app.pop_screen()
                        self.app.push_screen(FilePickerScreen(source, files))
            except httpx.HTTPStatusError as exc:
                self.app.pop_screen()
                self.app.notify(
                    f"HTTP {exc.response.status_code}: {source.display_name}",
                    severity="error",
                )
            except Exception as exc:
                self.app.pop_screen()
                self.app.notify(str(exc), severity="error")


# ─── File Picker Screen ─────────────────────────────────────────────────────

class FilePickerScreen(Screen):
    BINDINGS = [Binding("escape", "go_back", "Back")]

    def __init__(self, source: QuizSource, files: list) -> None:
        super().__init__()
        self.source = source
        self.files = files

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="picker"):
            with Vertical(id="picker-box"):
                yield Static(
                    f"📂  {self.source.owner}/{self.source.repo}",
                    id="picker-title",
                )
                yield Static(
                    f"{len(self.files)} quiz files found — pick one:",
                )
                yield ListView(
                    *[
                        ListItem(Label(f.path), name=f.path)
                        for f in self.files
                    ],
                    id="file-list",
                )
                yield Button("← Back", id="back-btn")
        yield Footer()

    @on(ListView.Selected, "#file-list")
    def handle_select(self, event: ListView.Selected) -> None:
        path = event.item.name
        self.source.path = path
        self.app.pop_screen()
        self.app.push_screen(LoadingScreen(self.source))

    @on(Button.Pressed, "#back-btn")
    def handle_back(self) -> None:
        self.action_go_back()

    def action_go_back(self) -> None:
        self.app.pop_screen()


# ─── Quiz Screen ─────────────────────────────────────────────────────────────

class QuizScreen(Screen):
    BINDINGS = [
        Binding("enter", "submit", "Submit", show=True),
        Binding("n", "next_question", "Next", show=True),
        Binding("h", "show_hint", "Hint", show=True),
        Binding("q", "quit_quiz", "Quit quiz", show=True),
    ]

    current_index: reactive[int] = reactive(0)

    def __init__(self, quiz: Quiz) -> None:
        super().__init__()
        self.quiz = quiz
        self.questions = list(quiz.questions)
        # Shuffle questions if configured
        if quiz.frontmatter.get("shuffle_questions"):
            random.shuffle(self.questions)
        self.answers: list[AnswerRecord | None] = [None] * len(self.questions)
        self.selected_choices: set[int] = set()
        self.submitted = False
        self.deferred = quiz.frontmatter.get("feedback_mode") == "deferred"
        self.points_per_correct = quiz.frontmatter.get("scoring", {}).get(
            "correct", 1
        )
        self.points_per_incorrect = quiz.frontmatter.get("scoring", {}).get(
            "incorrect", 0
        )

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal(id="quiz-header"):
            yield Static(self.quiz.title or "Quiz", id="quiz-title")
            yield Static("", id="quiz-progress")
        with VerticalScroll(id="question-area"):
            yield Static("", id="q-number")
            yield Markdown("", id="q-body")
            yield Static("", id="q-hint")
            yield Container(id="choices-container")
            yield Input(placeholder="Type your answer…", id="open-input")
            with Container(id="feedback-area"):
                yield Static("", id="feedback-correct")
                yield Static("", id="feedback-wrong")
                yield Static("", id="feedback-text")
        with Horizontal(id="nav-bar"):
            yield Button("← Prev", id="prev-btn")
            yield Button("Submit", variant="primary", id="submit-btn")
            yield Button("Next →", variant="primary", id="next-btn")
            yield Button("Finish", variant="warning", id="finish-btn")
        yield Footer()

    def on_mount(self) -> None:
        self._render_question()

    def watch_current_index(self) -> None:
        self._render_question()

    def _current_q(self) -> Question:
        return self.questions[self.current_index]

    def _render_question(self) -> None:
        idx = self.current_index
        q = self._current_q()
        total = len(self.questions)

        # Progress
        self.query_one("#quiz-progress", Static).update(
            f"Q{idx + 1}/{total}"
        )

        # Question number + title
        title_part = f" · {q.title}" if q.title else ""
        self.query_one("#q-number", Static).update(
            f"Question {idx + 1}{title_part}"
        )

        # Body
        body_md = q.body.strip() if q.body else ""
        self.query_one("#q-body", Markdown).update(body_md)

        # Hint
        hint_w = self.query_one("#q-hint", Static)
        hint_w.remove_class("visible")

        # Reset state
        self.selected_choices = set()
        answer = self.answers[idx]
        self.submitted = answer is not None

        # Choices
        container = self.query_one("#choices-container", Container)
        container.remove_children()

        open_input = self.query_one("#open-input", Input)

        if q.q_type in ("mcq", "multi", "tf"):
            open_input.display = False
            shuffled = list(enumerate(q.choices))
            if (
                q.q_type != "tf"
                and self.quiz.frontmatter.get("shuffle_answers", True)
                and q.meta.get("shuffle_answers", True) is not False
            ):
                random.shuffle(shuffled)
            for display_idx, (orig_idx, choice) in enumerate(shuffled):
                label = f"  {chr(65 + display_idx)})  {choice.text}"
                btn = Button(label, classes="choice-btn", name=str(orig_idx))
                container.mount(btn)
            container.mount(Static("", id="choice-feedback"))
        elif q.q_type == "open":
            open_input.display = True
            open_input.value = ""
            open_input.focus()
        elif q.q_type == "match":
            open_input.display = False
            lines = ["**Match the pairs:**\n"]
            for pair in q.match_pairs:
                lines.append(f"- {pair.left} → {pair.right}")
            container.mount(Markdown("\n".join(lines)))
        elif q.q_type == "order":
            open_input.display = False
            lines = ["**Correct order:**\n"]
            for i, item in enumerate(q.order_items, 1):
                lines.append(f"{i}. {item}")
            container.mount(Markdown("\n".join(lines)))
        else:
            open_input.display = False

        # Feedback area
        fb = self.query_one("#feedback-area", Container)
        fb.remove_class("visible")
        self.query_one("#feedback-correct", Static).update("")
        self.query_one("#feedback-wrong", Static).update("")
        self.query_one("#feedback-text", Static).update("")

        # If already answered, restore visual state
        if self.submitted:
            self._reveal_answer()

        # Nav visibility
        self.query_one("#prev-btn", Button).display = idx > 0
        self.query_one("#submit-btn", Button).display = not self.submitted
        self.query_one("#next-btn", Button).display = (
            self.submitted and idx < total - 1
        )
        self.query_one("#finish-btn", Button).display = (
            self.submitted and idx == total - 1
        )

    @on(Button.Pressed, ".choice-btn")
    def handle_choice(self, event: Button.Pressed) -> None:
        if self.submitted:
            return
        q = self._current_q()
        orig_idx = int(event.button.name)

        if q.q_type == "multi":
            # Toggle
            if orig_idx in self.selected_choices:
                self.selected_choices.discard(orig_idx)
                event.button.remove_class("selected")
            else:
                self.selected_choices.add(orig_idx)
                event.button.add_class("selected")
        else:
            # Single select
            for btn in self.query(".choice-btn"):
                btn.remove_class("selected")
            self.selected_choices = {orig_idx}
            event.button.add_class("selected")

    @on(Button.Pressed, "#submit-btn")
    def handle_submit_btn(self) -> None:
        self.action_submit()

    @on(Button.Pressed, "#next-btn")
    def handle_next_btn(self) -> None:
        self.action_next_question()

    @on(Button.Pressed, "#prev-btn")
    def handle_prev_btn(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1

    @on(Button.Pressed, "#finish-btn")
    def handle_finish_btn(self) -> None:
        self._show_results()

    @on(Input.Submitted, "#open-input")
    def handle_open_submit(self) -> None:
        self.action_submit()

    def action_submit(self) -> None:
        if self.submitted:
            return
        q = self._current_q()
        idx = self.current_index

        if q.q_type in ("mcq", "multi", "tf"):
            if not self.selected_choices:
                self.notify("Select an answer first", severity="warning")
                return
            correct_indices = {
                i for i, c in enumerate(q.choices) if c.correct
            }
            is_correct = self.selected_choices == correct_indices
            points_possible = float(q.meta.get("points", self.points_per_correct))
            points = points_possible if is_correct else float(self.points_per_incorrect)
            self.answers[idx] = AnswerRecord(
                question_number=q.number,
                correct=is_correct,
                points_earned=points,
                points_possible=points_possible,
            )

        elif q.q_type == "open":
            user_answer = self.query_one("#open-input", Input).value.strip()
            if not user_answer:
                self.notify("Type an answer first", severity="warning")
                return
            expected = q.open_answer.strip().lower()
            # Support pipe-separated alternatives
            alternatives = [a.strip().lower() for a in expected.split("|")]
            is_correct = user_answer.lower() in alternatives
            points_possible = float(q.meta.get("points", self.points_per_correct))
            points = points_possible if is_correct else float(self.points_per_incorrect)
            self.answers[idx] = AnswerRecord(
                question_number=q.number,
                correct=is_correct,
                points_earned=points,
                points_possible=points_possible,
            )
        else:
            # match/order — display-only for now, auto-correct
            points_possible = float(q.meta.get("points", self.points_per_correct))
            self.answers[idx] = AnswerRecord(
                question_number=q.number,
                correct=True,
                points_earned=points_possible,
                points_possible=points_possible,
            )

        self.submitted = True

        if not self.deferred:
            self._reveal_answer()

        # Update nav
        total = len(self.questions)
        self.query_one("#submit-btn", Button).display = False
        self.query_one("#next-btn", Button).display = (
            self.current_index < total - 1
        )
        self.query_one("#finish-btn", Button).display = (
            self.current_index == total - 1
        )

    def _reveal_answer(self) -> None:
        q = self._current_q()
        answer = self.answers[self.current_index]
        if answer is None:
            return

        if q.q_type in ("mcq", "multi", "tf"):
            for btn in self.query(".choice-btn"):
                orig_idx = int(btn.name)
                choice = q.choices[orig_idx]
                btn.remove_class("selected")
                if choice.correct:
                    btn.add_class("correct-reveal")
                elif orig_idx in self.selected_choices:
                    btn.add_class("wrong-reveal")

                # Show per-choice feedback
                if orig_idx in self.selected_choices and choice.feedback:
                    try:
                        fb_label = self.query_one("#choice-feedback", Static)
                        fb_label.update(f"  💬 {choice.feedback}")
                        fb_label.add_class("visible")
                    except NoMatches:
                        pass

        # Global feedback
        fb_area = self.query_one("#feedback-area", Container)
        if answer.correct:
            self.query_one("#feedback-correct", Static).update("✅ Correct!")
        else:
            self.query_one("#feedback-wrong", Static).update("❌ Incorrect")
            if q.q_type == "open":
                self.query_one("#feedback-wrong", Static).update(
                    f"❌ Incorrect — expected: {q.open_answer}"
                )

        if q.feedback:
            self.query_one("#feedback-text", Static).update(q.feedback)

        fb_area.add_class("visible")

    def action_next_question(self) -> None:
        if self.current_index < len(self.questions) - 1:
            self.current_index += 1

    def action_show_hint(self) -> None:
        q = self._current_q()
        hint = q.meta.get("hint", "")
        if hint:
            hint_w = self.query_one("#q-hint", Static)
            hint_w.update(f"💡 Hint: {hint}")
            hint_w.add_class("visible")
        else:
            self.notify("No hint available for this question", severity="information")

    def action_quit_quiz(self) -> None:
        self._show_results()

    def _show_results(self) -> None:
        self.app.pop_screen()
        self.app.push_screen(
            ResultsScreen(self.quiz, self.questions, self.answers)
        )


# ─── Results Screen ─────────────────────────────────────────────────────────

class ResultsScreen(Screen):
    BINDINGS = [
        Binding("r", "replay", "Replay", show=True),
        Binding("q", "go_home", "Home", show=True),
    ]

    def __init__(
        self,
        quiz: Quiz,
        questions: list[Question],
        answers: list[AnswerRecord | None],
    ) -> None:
        super().__init__()
        self.quiz = quiz
        self.questions = questions
        self.answers = answers

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Container(id="results"):
            with VerticalScroll(id="results-box"):
                yield Static("🏁  Results", id="results-title")
                yield Static("", id="score-display")
                yield Static("", id="pass-fail")
                yield ProgressBar(total=100, show_eta=False, id="score-bar")
                yield Static("Breakdown:", id="breakdown-title")
                yield Container(id="breakdown-container")
                yield Button("▶  Play again", variant="primary", id="replay-btn")
                yield Button("🏠  Home", id="home-btn")
        yield Footer()

    def on_mount(self) -> None:
        total_possible = 0.0
        total_earned = 0.0
        answered = 0
        correct_count = 0

        for i, a in enumerate(self.answers):
            q = self.questions[i]
            pts = float(q.meta.get("points", self.quiz.frontmatter.get("scoring", {}).get("correct", 1)))
            total_possible += pts
            if a is not None:
                answered += 1
                total_earned += a.points_earned
                if a.correct:
                    correct_count += 1

        pct = (total_earned / total_possible * 100) if total_possible > 0 else 0
        self.query_one("#score-display", Static).update(
            f"{total_earned:.0f} / {total_possible:.0f} points  ({pct:.0f}%)"
        )
        self.query_one("#score-bar", ProgressBar).update(progress=pct)

        passing = self.quiz.frontmatter.get("passing_score")
        pf = self.query_one("#pass-fail", Static)
        if passing is not None:
            ratio = total_earned / total_possible if total_possible else 0
            if ratio >= passing:
                pf.update(f"✅ PASSED (≥{passing * 100:.0f}%)")
                pf.add_class("pass")
            else:
                pf.update(f"❌ FAILED (<{passing * 100:.0f}%)")
                pf.add_class("fail")

        # Breakdown
        container = self.query_one("#breakdown-container", Container)
        for i, a in enumerate(self.answers):
            q = self.questions[i]
            title = q.title or f"Question {q.number}"
            if a is None:
                line = Static(
                    f"  ⏭  Q{i + 1}: {title} — skipped",
                    classes="result-line result-skip",
                )
            elif a.correct:
                line = Static(
                    f"  ✅ Q{i + 1}: {title} — {a.points_earned:.0f} pts",
                    classes="result-line result-correct",
                )
            else:
                line = Static(
                    f"  ❌ Q{i + 1}: {title} — {a.points_earned:.0f} pts",
                    classes="result-line result-wrong",
                )
            container.mount(line)

    @on(Button.Pressed, "#replay-btn")
    def handle_replay(self) -> None:
        self.action_replay()

    @on(Button.Pressed, "#home-btn")
    def handle_home(self) -> None:
        self.action_go_home()

    def action_replay(self) -> None:
        self.app.pop_screen()
        self.app.push_screen(QuizScreen(self.quiz))

    def action_go_home(self) -> None:
        self.app.pop_screen()
        self.app.push_screen(WelcomeScreen())


# ─── Main App ────────────────────────────────────────────────────────────────

class QuizMDApp(App):
    """QuizMD TUI — play quizzes in your terminal."""

    TITLE = "QuizMD TUI"
    CSS = CSS
    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", show=True, priority=True),
    ]

    def __init__(self, source: str | None = None) -> None:
        super().__init__()
        self._initial_source = source

    def on_mount(self) -> None:
        if self._initial_source:
            try:
                src = parse_source(self._initial_source)
                self.push_screen(LoadingScreen(src))
            except ValueError:
                self.push_screen(WelcomeScreen())
                self.notify(
                    f"Invalid source: {self._initial_source}", severity="error"
                )
        else:
            self.push_screen(WelcomeScreen())
