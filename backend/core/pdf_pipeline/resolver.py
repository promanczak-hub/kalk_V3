import copy
from core.pdf_pipeline.schemas import ParsedPriceList


class FootnoteResolver:
    """Class responsible for deterministically resolving footnotes in the parsed price list."""

    def resolve(self, parsed_data: ParsedPriceList) -> ParsedPriceList:
        """
        Resolves footnotes by appending their text to the elements referencing them.

        Args:
            parsed_data: The parsed price list containing footnotes and elements.

        Returns:
            A new ParsedPriceList with resolved footnotes appended to relevant fields.
        """
        if not parsed_data.footnotes:
            return parsed_data

        # Create a dictionary for O(1) attribute lookup and avoid modifying incoming data
        data_copy = copy.deepcopy(parsed_data)

        # Clean footnote references to match exact strings (e.g., "*1", "1)", "(1)")
        footnote_map = {
            fn.reference.strip(): fn.text.strip() for fn in data_copy.footnotes
        }

        # Resolve in engines
        for engine in data_copy.engines:
            self._resolve_string_field(engine, "engine_name", footnote_map)
            for trim_pricing in engine.prices_by_trim:
                self._resolve_string_field(trim_pricing, "trim_name", footnote_map)

        # Resolve in features
        for feature in data_copy.features:
            self._resolve_string_field(feature, "name", footnote_map)
            self._resolve_string_field(feature, "availability_rules", footnote_map)

        return data_copy

    def _resolve_string_field(
        self, obj: any, field_name: str, footnote_map: dict[str, str]
    ) -> None:
        """Helper to append footnote text to a specific string field based on matched references."""
        current_value = getattr(obj, field_name, None)

        if not isinstance(current_value, str) or not current_value:
            return

        appended_texts = []
        for ref, text in footnote_map.items():
            # Check if reference exists in the string.
            # Using simple 'in' for edge cases where regex word boundaries \b might fail on symbols like *
            if ref in current_value:
                appended_texts.append(f"[{ref}: {text}]")

        if appended_texts:
            new_value = f"{current_value} " + " ".join(appended_texts)
            setattr(obj, field_name, new_value)
