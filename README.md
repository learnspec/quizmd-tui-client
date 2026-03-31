# QuizMD TUI

Play [QuizMD](https://github.com/learnspec/quizmd) quizzes right in your terminal.

Built with [Textual](https://textual.textualize.io/) and [pylearnspec](https://github.com/learnspec/pylearnspec).

![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue)
![License MIT](https://img.shields.io/badge/license-MIT-green)

## Features

- Fetch `.quiz.md` files from any GitHub repo or URL
- Browse repos with multiple quiz files via a built-in file picker
- Play MCQ, multi-select, true/false, and open-answer questions
- Immediate or deferred feedback modes (respects quiz frontmatter)
- Per-question hints, per-choice feedback, and global explanations
- Scoring with pass/fail thresholds
- Question and answer shuffling
- Full results breakdown with replay

## Install

```bash
pip install quizmd-tui
```

Or from source:

```bash
git clone https://github.com/learnspec/quizmd-tui-client.git
cd quizmd-tui-client
pip install -e .
```

## Usage

```bash
# Interactive — enter a source in the TUI
quizmd

# Direct — point to a repo
quizmd learnspec/quizmd

# Direct — point to a specific file
quizmd https://github.com/learnspec/quizmd/blob/main/examples/baroque-music.quiz.md
```

## Keyboard shortcuts

| Key     | Action                     |
|---------|----------------------------|
| Enter   | Submit answer              |
| n       | Next question              |
| h       | Show hint (if available)   |
| r       | Replay (on results screen) |
| q       | Quit quiz / go home        |
| Ctrl+C  | Exit                       |

## Supported question types

| Type         | Support |
|--------------|---------|
| MCQ          | Full    |
| Multi-select | Full    |
| True/False   | Full    |
| Open answer  | Full    |
| Match pairs  | Display |
| Order        | Display |

## License

MIT
