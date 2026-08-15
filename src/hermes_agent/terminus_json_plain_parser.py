import json
import re
from dataclasses import dataclass
from typing import List


@dataclass
class ParsedCommand:
    keystrokes: str
    duration: float


@dataclass
class ParseResult:
    commands: List[ParsedCommand]
    is_task_complete: bool
    error: str
    warning: str


class TerminusJSONPlainParser:
    """Parser for terminus JSON plain response format."""

    def __init__(self):
        self.required_fields = ["analysis", "plan", "commands"]

    def parse_response(self, response: str) -> ParseResult:
        """
        Parse a terminus JSON plain response and extract commands.

        Args:
            response: The full LLM response string

        Returns:
            ParseResult with commands, completion status, errors and warnings
        """

        # Pre-process: strip markdown code fences BEFORE any parsing attempt.
        # This prevents "Extra text detected" warnings that confuse the LLM.
        # DeepSeek V4 Flash frequently wraps JSON in ```json ... ``` blocks.
        cleaned_response = self._strip_markdown_fences(response)

        # Try normal parsing first
        result = self._try_parse_response(cleaned_response)

        if result.error:
            # Try auto-fixes in order until one works.
            # Use cleaned_response as the base (already has fences stripped),
            # so auto-fixes work on the clean JSON content.
            for fix_name, fix_function in self._get_auto_fixes():
                corrected_response, was_fixed = fix_function(
                    cleaned_response, result.error
                )
                if was_fixed:
                    corrected_result = self._try_parse_response(corrected_response)

                    if corrected_result.error == "":
                        # Success! Add auto-correction warning
                        auto_warning = (
                            f"AUTO-CORRECTED: {fix_name} - "
                            "please fix this in future responses"
                        )
                        corrected_result.warning = self._combine_warnings(
                            auto_warning, corrected_result.warning
                        )
                        return corrected_result

        # Return original result if no fix worked
        return result

    def _try_parse_response(self, response: str) -> ParseResult:
        """
        Try to parse a terminus JSON plain response.

        Args:
            response: The full LLM response string

        Returns:
            ParseResult with commands, completion status, errors and warnings
        """
        warnings = []

        # Check for extra text before/after JSON
        json_content, extra_text_warnings = self._extract_json_content(response)
        warnings.extend(extra_text_warnings)

        if not json_content:
            return ParseResult(
                [],
                False,
                "No valid JSON found in response",
                "- " + "\n- ".join(warnings) if warnings else "",
            )

        # Parse JSON
        try:
            parsed_data = json.loads(json_content)
        except json.JSONDecodeError as e:
            # Add debug info
            error_msg = f"Invalid JSON: {str(e)}"
            if len(json_content) < 200:
                error_msg += f" | Content: {repr(json_content)}"
            else:
                error_msg += f" | Content preview: {repr(json_content[:100])}..."
            return ParseResult(
                [], False, error_msg, "- " + "\n- ".join(warnings) if warnings else ""
            )

        # Validate structure
        validation_error = self._validate_json_structure(
            parsed_data, json_content, warnings
        )
        if validation_error:
            return ParseResult(
                [],
                False,
                validation_error,
                "- " + "\n- ".join(warnings) if warnings else "",
            )

        # Check if task is complete
        is_complete = parsed_data.get("task_complete", False)
        if isinstance(is_complete, str):
            is_complete = is_complete.lower() in ("true", "1", "yes")

        # Parse commands
        commands_data = parsed_data.get("commands", [])
        commands, parse_error = self._parse_commands(commands_data, warnings)
        if parse_error:
            # If task is complete, parse errors are just warnings
            if is_complete:
                warnings.append(parse_error)
                return ParseResult(
                    [], True, "", "- " + "\n- ".join(warnings) if warnings else ""
                )
            return ParseResult(
                [], False, parse_error, "- " + "\n- ".join(warnings) if warnings else ""
            )

        return ParseResult(
            commands, is_complete, "", "- " + "\n- ".join(warnings) if warnings else ""
        )

    @staticmethod
    def _is_only_markdown_or_whitespace(text: str) -> bool:
        """Check if text consists only of markdown formatting and whitespace.

        Returns True if text contains only backticks, whitespace, and
        optional language identifiers (like 'json', 'javascript').
        """
        cleaned = text.strip()
        if not cleaned:
            return True
        # Allow: ```, ``, `, json, javascript, js, and whitespace
        return bool(re.match(r"^[`\s]*(?:json|javascript|js)?[`\s]*$", cleaned))

    def _should_skip_extra_text_warning(self, text: str) -> bool:
        """Check if extra text should be skipped (no warning generated).

        Returns True for markdown fences, natural language descriptions,
        and common LLM conversational prefixes.
        """
        cleaned = text.strip()
        if not cleaned:
            return True
        # Markdown fences
        if self._is_only_markdown_or_whitespace(cleaned):
            return True
        # Common LLM conversational prefixes, such as "Here is my response".
        # These almost always precede valid JSON and are harmless
        return (
            True  # Generously skip all extra text warnings to avoid confusing the LLM
        )

    def _extract_json_content(self, response: str) -> tuple[str, List[str]]:
        """Extract JSON content from response, handling extra text."""
        warnings = []

        # Try to find JSON object boundaries
        json_start = -1
        json_end = -1
        brace_count = 0
        in_string = False
        escape_next = False

        for i, char in enumerate(response):
            if escape_next:
                escape_next = False
                continue

            if char == "\\":
                escape_next = True
                continue

            if char == '"' and not escape_next:
                in_string = not in_string
                continue

            if not in_string:
                if char == "{":
                    if brace_count == 0:
                        json_start = i
                    brace_count += 1
                elif char == "}":
                    brace_count -= 1
                    if brace_count == 0 and json_start != -1:
                        json_end = i + 1
                        break

        if json_start == -1 or json_end == -1:
            return "", ["No valid JSON object found"]

        # Check for extra text (skip warnings for harmless LLM conversational text)
        before_text = response[:json_start].strip()
        after_text = response[json_end:].strip()

        if before_text and not self._should_skip_extra_text_warning(before_text):
            warnings.append("Extra text detected before JSON object")
        if after_text and not self._should_skip_extra_text_warning(after_text):
            warnings.append("Extra text detected after JSON object")

        return response[json_start:json_end], warnings

    def _validate_json_structure(
        self, data: dict, json_content: str, warnings: List[str]
    ) -> str:
        """Validate the JSON structure has required fields."""
        if not isinstance(data, dict):
            return "Response must be a JSON object"

        # Check for required fields
        missing_fields = []
        for field in self.required_fields:
            if field not in data:
                missing_fields.append(field)

        if missing_fields:
            return f"Missing required fields: {', '.join(missing_fields)}"

        # Validate field types
        if not isinstance(data.get("analysis", ""), str):
            warnings.append("Field 'analysis' should be a string")

        if not isinstance(data.get("plan", ""), str):
            warnings.append("Field 'plan' should be a string")

        commands = data.get("commands", [])
        if not isinstance(commands, list):
            return "Field 'commands' must be an array"

        # Validate task_complete if present
        task_complete = data.get("task_complete")
        if task_complete is not None and not isinstance(task_complete, (bool, str)):
            warnings.append("Field 'task_complete' should be a boolean or string")

        return ""

    def _parse_commands(
        self, commands_data: List[dict], warnings: List[str]
    ) -> tuple[List[ParsedCommand], str]:
        """Parse commands array into ParsedCommand objects."""
        commands = []

        for i, cmd_data in enumerate(commands_data):
            if not isinstance(cmd_data, dict):
                return [], f"Command {i + 1} must be an object"

            # Check for required keystrokes field
            if "keystrokes" not in cmd_data:
                return [], f"Command {i + 1} missing required 'keystrokes' field"

            keystrokes = cmd_data["keystrokes"]
            if not isinstance(keystrokes, str):
                return [], f"Command {i + 1} 'keystrokes' must be a string"

            # Parse optional fields with defaults
            if "duration" in cmd_data:
                duration = cmd_data["duration"]
                if not isinstance(duration, (int, float)):
                    warnings.append(
                        f"Command {i + 1}: Invalid duration value, using default 1.0"
                    )
                    duration = 1.0
            else:
                warnings.append(
                    f"Command {i + 1}: Missing duration field, using default 1.0"
                )
                duration = 1.0

            # Check for unknown fields
            known_fields = {"keystrokes", "duration"}
            unknown_fields = set(cmd_data.keys()) - known_fields
            if unknown_fields:
                warnings.append(
                    f"Command {i + 1}: Unknown fields: {', '.join(unknown_fields)}"
                )

            # Check for newline at end of keystrokes if followed by another command
            if i < len(commands_data) - 1 and not keystrokes.endswith("\n"):
                warnings.append(
                    f"Command {i + 1} should end with newline when followed "
                    "by another command. Otherwise the two commands will be "
                    "concatenated together on the same line."
                )

            commands.append(
                ParsedCommand(keystrokes=keystrokes, duration=float(duration))
            )

        return commands, ""

    def _strip_markdown_fences(self, response: str) -> str:
        """Strip markdown code fences from response string pre-emptively.

        This is called BEFORE parsing to prevent "Extra text detected" warnings.
        DeepSeek V4 Flash frequently wraps JSON in markdown code blocks like:
          ```json\n{...}\n```

        Returns the cleaned response string.
        """
        # Pattern 1: ```json ... ``` (with language tag)
        pattern1 = r"```(?:json|javascript|js)\s*\n?(.*?)```"
        match = re.search(pattern1, response, re.DOTALL)
        if match:
            return match.group(1).strip()

        # Pattern 2: ``` ... ``` (generic code fence)
        pattern2 = r"```\s*\n?(.*?)```"
        match = re.search(pattern2, response, re.DOTALL)
        if match:
            return match.group(1).strip()

        return response

    def _get_auto_fixes(self):
        """Return list of auto-fix functions to try in order."""
        return [
            (
                "Stripped markdown code fences from response",
                self._fix_markdown_code_fences,
            ),
            (
                "Fixed incomplete JSON by adding missing closing brace",
                self._fix_incomplete_json,
            ),
            ("Extracted JSON from mixed content", self._fix_mixed_content),
        ]

    def _fix_markdown_code_fences(self, response: str, error: str) -> tuple[str, bool]:
        """Strip markdown code fences (```json ... ```) from response."""
        # Pattern 1: ```json ... ``` (with language tag)
        pattern1 = r"```(?:json|javascript|js)\s*\n?(.*?)```"
        match = re.search(pattern1, response, re.DOTALL)
        if match:
            return match.group(1).strip(), True

        # Pattern 2: ``` ... ``` (generic code fence)
        pattern2 = r"```\s*\n?(.*?)```"
        match = re.search(pattern2, response, re.DOTALL)
        if match:
            return match.group(1).strip(), True

        # Pattern 3: Single backtick code block
        pattern3 = r"`(.*?)`"
        match = re.search(pattern3, response, re.DOTALL)
        if match:
            content = match.group(1).strip()
            if content.startswith("{") and content.endswith("}"):
                return content, True

        return response, False

    def _fix_incomplete_json(self, response: str, error: str) -> tuple[str, bool]:
        """Fix incomplete JSON by adding missing closing braces."""
        if (
            "Invalid JSON" in error
            or "Expecting" in error
            or "Unterminated" in error
            or "No valid JSON found" in error
        ):
            # Try adding closing braces
            brace_count = response.count("{") - response.count("}")
            if brace_count > 0:
                fixed = response + "}" * brace_count
                return fixed, True
        return response, False

    def _fix_mixed_content(self, response: str, error: str) -> tuple[str, bool]:
        """Extract JSON from response with mixed content."""
        # Look for JSON-like patterns
        json_pattern = r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}"
        matches = re.findall(json_pattern, response, re.DOTALL)

        for match in matches:
            try:
                json.loads(match)
                return match, True
            except json.JSONDecodeError:
                continue

        return response, False

    def _combine_warnings(self, auto_warning: str, existing_warning: str) -> str:
        """Combine auto-correction warning with existing warnings."""
        if existing_warning:
            return f"- {auto_warning}\n{existing_warning}"
        else:
            return f"- {auto_warning}"
