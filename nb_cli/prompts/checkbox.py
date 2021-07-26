import os
from typing import Set, List, Tuple, Optional

from prompt_toolkit.styles import Style
from prompt_toolkit.filters import is_done
from prompt_toolkit.formatted_text import AnyFormattedText
from prompt_toolkit.key_binding import KeyBindings, KeyPressEvent

from prompt_toolkit.layout import Layout
from prompt_toolkit.layout.dimension import Dimension
from prompt_toolkit.layout.controls import FormattedTextControl
from prompt_toolkit.layout.containers import HSplit, Window, ConditionalContainer

from . import BasePrompt, NoAnswer, Choice


class CheckboxPrompt(BasePrompt[Tuple[Choice, ...]]):
    """Checkbox Prompt that supports auto scrolling.
    
    Style class guide:
    
    ```
    [?] Choose a choice and return? (Use ↑ and ↓ to move, Space to select, Enter to submit)
    └┬┘ └──────────────┬──────────┘ └───────────────────────┬─────────────────────────────┘
    questionmark    question                            annotation
    
     ❯  ●  choice selected
    └┬┘└┬┘ └───────┬─────┘
    pointer sign selected
    
        ○  choice unselected
       └┬┘ └───────┬───────┘
      unsign   unselected
    ```
    """

    def __init__(
            self,
            question: str,
            choices: List[Choice],
            question_mark: str = "[?]",
            pointer: str = "❯",
            selected_sign: str = "●",
            unselected_sign: str = "○",
            annotation:
        str = "(Use ↑ and ↓ to move, Space to select, Enter to submit)",
            max_height: Optional[int] = None):
        self.question: str = question
        self.choices: List[Choice] = choices
        self.question_mark: str = question_mark
        self.pointer: str = pointer
        self.selected_sign: str = selected_sign
        self.unselected_sign: str = unselected_sign
        self.annotation: str = annotation
        self._index: int = 0
        self._display_index: int = 0
        self._answered: bool = False
        self._selected: Set[int] = set()
        self._max_height: Optional[int] = max_height

    @property
    def max_height(self) -> int:
        return self._max_height or os.get_terminal_size().lines

    def _build_layout(self) -> Layout:
        layout = Layout(
            HSplit([
                Window(FormattedTextControl(self._get_prompt),
                       height=Dimension(1),
                       dont_extend_height=True,
                       always_hide_cursor=True),
                ConditionalContainer(
                    Window(FormattedTextControl(self._get_choices_prompt),
                           height=Dimension(1),
                           dont_extend_height=True), ~is_done)
            ]))
        return layout

    def _build_style(self, style: Style) -> Style:
        default = Style([("questionmark", "fg:#5F819D"), ("question", "bold"),
                         ("answer", "fg:#FF9D00"), ("annotation", "fg:#7F8C8D"),
                         ("selected", "fg:ansigreen noreverse")])
        return Style([*default.style_rules, *style.style_rules])

    def _build_keybindings(self) -> KeyBindings:
        kb = KeyBindings()

        @kb.add("up", eager=True)
        def previous(event: KeyPressEvent):
            self._index = (self._index - 1) % len(self.choices)
            if self._index == self._display_index and self._display_index > 0:
                self._display_index -= 1
            elif self._index == len(self.choices) - 1:
                start_index = len(self.choices) - self.max_height + 1
                self._display_index = 0 if start_index < 0 else start_index

        @kb.add("down", eager=True)
        def next(event: KeyPressEvent):
            self._index = (self._index + 1) % len(self.choices)
            end_index = self._display_index + self.max_height - 2
            if self._index == end_index and end_index < len(self.choices) - 1:
                self._display_index += 1
            elif self._index == 0:
                self._display_index = 0

        @kb.add("space", eager=True)
        def select(event: KeyPressEvent):
            if self._index not in self._selected:
                self._selected.add(self._index)
            else:
                self._selected.remove(self._index)

        @kb.add("enter", eager=True)
        def enter(event: KeyPressEvent):
            self._answered = True
            event.app.exit(result=self._get_result())

        @kb.add("c-c", eager=True)
        @kb.add("c-q", eager=True)
        def quit(event: KeyPressEvent):
            event.app.exit(result=NoAnswer)

        return kb

    def _get_prompt(self) -> AnyFormattedText:
        prompts: AnyFormattedText = [("class:questionmark", self.question_mark),
                                     ("", " "),
                                     ("class:question", self.question.strip()),
                                     ("", " ")]
        if self._answered:
            result = self._get_result()
            prompts.append(
                ("class:answer",
                 ", ".join(choice.name.strip() for choice in result)))
        else:
            prompts.append(("class:annotation", self.annotation))
        return prompts

    def _get_choices_prompt(self) -> AnyFormattedText:
        max_num = self.max_height - 1

        prompts: AnyFormattedText = []
        for index, choice in enumerate(
                self.choices[self._display_index:self._display_index +
                             max_num]):
            if index + self._display_index == self._index:
                prompts.append(("class:pointer", self.pointer))
                prompts.append(("", " "))
            else:
                prompts.append(("", " " * len(self.pointer)))
                prompts.append(("", " "))
            if index + self._display_index in self._selected:
                prompts.append(("class:sign", self.selected_sign))
                prompts.append(("", " "))
                prompts.append(("class:selected", choice.name.strip() + "\n"))
            else:
                prompts.append(("class:unsign", self.unselected_sign))
                prompts.append(("", " "))
                prompts.append(("class:unselected", choice.name.strip() + "\n"))
        return prompts

    def _get_result(self) -> Tuple[Choice, ...]:
        return tuple(choice for index, choice in enumerate(self.choices)
                     if index in self._selected)