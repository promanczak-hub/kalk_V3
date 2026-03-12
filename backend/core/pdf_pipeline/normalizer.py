from core.pdf_pipeline.schemas import ParsedPriceList


class StrictNormalizer:
    """
    Class responsible for strict normalization and basic data cleaning.
    No fuzzy logic is used to avoid hallucinations. Missing numeric values default to 0.0.
    """

    def normalize(self, parsed_data: ParsedPriceList) -> ParsedPriceList:
        """
        Normalizes the parsed price list in place (or returns a normalized structure).
        Ensures strict type casting, strip() on strings, and 0.0 for missing prices.
        """
        # We can mutate the instance or create a copy, but here we'll just mutate since it's the end of pipeline processing

        parsed_data.brand = self._clean_string(parsed_data.brand)
        parsed_data.model = self._clean_string(parsed_data.model)

        if parsed_data.valid_from:
            parsed_data.valid_from = self._clean_string(parsed_data.valid_from)

        if parsed_data.model_year:
            parsed_data.model_year = self._clean_string(parsed_data.model_year)

        for engine in parsed_data.engines:
            engine.engine_name = self._clean_string(engine.engine_name)
            engine.transmission = self._clean_string(engine.transmission)
            engine.fuel_type = self._clean_string(engine.fuel_type)

            for trim in engine.prices_by_trim:
                trim.trim_name = self._clean_string(trim.trim_name)
                # Enforce 0.0 on None
                if trim.price_netto is None:
                    trim.price_netto = 0.0
                if trim.price_brutto is None:
                    trim.price_brutto = 0.0

        for feature in parsed_data.features:
            feature.name = self._clean_string(feature.name)
            if feature.code:
                feature.code = self._clean_string(feature.code)
            if feature.availability_rules:
                feature.availability_rules = self._clean_string(
                    feature.availability_rules
                )

            # Arrays logic
            if feature.applicable_trims:
                feature.applicable_trims = [
                    self._clean_string(t) for t in feature.applicable_trims
                ]

            # Enforce 0.0 on None
            if feature.price_netto is None:
                feature.price_netto = 0.0
            if feature.price_brutto is None:
                feature.price_brutto = 0.0

        return parsed_data

    def _clean_string(self, value: str) -> str:
        """Strips whitespace, replaces multiple spaces with a single space."""
        if not value:
            return ""
        # Clean double spaces logic
        import re

        return re.sub(r"\s+", " ", value).strip()
