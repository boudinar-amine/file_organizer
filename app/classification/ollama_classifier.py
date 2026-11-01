"""Optional Ollama-based LLM classifier for PDF documents.

Handles local Ollama communication safely:
1. Queries /api/tags to verify server health and inspect installed models.
2. If no models are installed or requested model is missing, reports cleanly ONCE
   and disables further calls for the batch (preventing repeated 404 loops).
3. Sends compact context (filename, metadata, max 1500 chars text).
4. Strictly validates returned JSON against expected schema.
"""

from __future__ import annotations

import json
from typing import Any, Optional

from app.database.models import (
    ClassificationResult,
    PDFContent,
    PDFFileInfo,
    PDFMetadata,
)
from app.utils.app_logging import get_logger
from app.utils.validators import validate_json_classification

logger = get_logger("classification.ollama")

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2"
_MAX_EXCERPT_CHARS = 1500


class OllamaClassifier:
    """Classify PDF documents using a local Ollama LLM.

    Attributes:
        base_url: The Ollama API base URL.
        model: The Ollama model name to use.
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_OLLAMA_URL,
        model: str = _DEFAULT_MODEL,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model
        self._disabled_for_session = False
        self._disable_reason = ""
        self._installed_models: list[str] = []
        self._checked_health = False

    def get_installed_models(self) -> list[str]:
        """Fetch the list of model names currently installed in Ollama."""
        try:
            import urllib.request

            req = urllib.request.Request(f"{self.base_url}/api/tags", method="GET")
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    models = [m.get("name", "") for m in data.get("models", [])]
                    self._installed_models = [m for m in models if m]
                    return self._installed_models
        except Exception:
            pass
        return []

    def is_available(self) -> bool:
        """Check whether Ollama is reachable AND has a usable model installed."""
        if self._disabled_for_session:
            return False

        models = self.get_installed_models()
        self._checked_health = True

        if not models:
            self._disabled_for_session = True
            self._disable_reason = (
                "Ollama is running at http://localhost:11434, but no models are downloaded yet. "
                "Download a model via terminal using: 'ollama pull llama3.2' or 'ollama pull mistral'."
            )
            logger.warning(self._disable_reason)
            return False

        # Check if the requested model exists (e.g. 'llama3.2' or 'llama3.2:latest')
        target = self.model.lower()
        has_target = any(
            target == m.lower() or target == m.split(":")[0].lower()
            for m in models
        )

        if not has_target:
            # Fallback to the first available installed model
            fallback = models[0]
            logger.info(
                "Model '%s' not found in Ollama. Auto-selecting installed model: '%s'",
                self.model,
                fallback,
            )
            self.model = fallback

        return True

    def classify(
        self,
        file_info: PDFFileInfo,
        metadata: Optional[PDFMetadata],
        content: Optional[PDFContent],
        user_domains: Optional[list[str]] = None,
    ) -> Optional[ClassificationResult]:
        """Classify a document using Ollama.

        If Ollama has no models or fails with 404, disables further queries
        for this session and returns None to let the rule classifier take over.
        """
        if self._disabled_for_session:
            return None

        if not self._checked_health:
            if not self.is_available():
                return None

        prompt = self._build_prompt(file_info, metadata, content, user_domains)
        raw_response = self._query_ollama(prompt)
        if raw_response is None:
            return None

        result = self._parse_response(raw_response)
        if result is not None:
            result.classifier_used = f"ollama ({self.model})"
        return result

    # ------------------------------------------------------------------
    # Prompt construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_prompt(
        file_info: PDFFileInfo,
        metadata: Optional[PDFMetadata],
        content: Optional[PDFContent],
        user_domains: Optional[list[str]] = None,
    ) -> str:
        """Build a compact, taxonomy-aware classification prompt for the LLM."""
        parts: list[str] = [
            "You are an expert document librarian and classifier.",
            "Analyze the document details below (which may be in English, French, or bilingual) and classify it.",
            "",
        ]

        if user_domains:
            parts.append("User's Professional Domains & Focus Areas:")
            for d in user_domains:
                parts.append(f"• {d}")
            parts.append("Prioritize classifying into these domains when relevant.")
            parts.append("")

        parts.extend([
            "Standard Primary Categories:",
            "- Research (Subcategories: Explainable AI, Machine Learning, Deep Learning, Scientific Articles, Theses)",
            "- Insurtech (Subcategories: Risk Modeling, Claims & Fraud, Underwriting, Analytics, Compliance)",
            "- Sécurité Sanitaire (Subcategories: Dispositifs Médicaux, Veille & Risques, Normes & Qualité, Épidémiologie)",
            "- Public Health (Subcategories: WHO, Epidemiology, Pharmacovigilance, Vaccination)",
            "- Administration (Subcategories: Invoices, Procurement, Contracts, Human Resources)",
            "- Legal (Subcategories: Regulations, Laws, Directives)",
            "- Strategy (Subcategories: Strategic Plans, Roadmaps, Action Plans)",
            "- Guides (Subcategories: Manuals, Procedures/SOPs, Specifications)",
            "- Meetings (Subcategories: Meeting Documents, Presentations)",
            "- Finance (Subcategories: Financial Reports, Budgets)",
            "",
            f"Filename: {file_info.filename}",
            f"File size: {file_info.size_human}",
        ])

        if metadata:
            if metadata.title:
                parts.append(f"PDF Title: {metadata.title}")
            if metadata.author:
                parts.append(f"PDF Author: {metadata.author}")
            if metadata.subject:
                parts.append(f"PDF Subject: {metadata.subject}")
            parts.append(f"Page count: {metadata.page_count}")

        if content and content.extracted_text:
            excerpt = content.extracted_text[:_MAX_EXCERPT_CHARS]
            parts.append(f"\nExtracted document text (excerpt):\n{excerpt}")

        parts.append(
            "\n"
            "Respond ONLY with a valid JSON object (no markdown, no backticks, no extra text):\n"
            "{\n"
            '  "document_type": "precise document type",\n'
            '  "category": "Primary Category",\n'
            '  "subcategory": "Subcategory",\n'
            '  "topic": "Concise main topic",\n'
            '  "organization": "Issuing organization if identifiable",\n'
            '  "year": "4-digit year if identifiable",\n'
            '  "confidence": 0.00 to 1.00,\n'
            '  "reason": "1-sentence reason for this classification"\n'
            "}"
        )

        return "\n".join(parts)

    # ------------------------------------------------------------------
    # Ollama communication
    # ------------------------------------------------------------------

    def _query_ollama(self, prompt: str) -> Optional[str]:
        """Send a prompt to Ollama and return the response text."""
        try:
            import urllib.error
            import urllib.request

            payload = json.dumps({
                "model": self.model,
                "prompt": prompt,
                "stream": False,
            }).encode("utf-8")

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )

            with urllib.request.urlopen(req, timeout=45) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return body.get("response", "")

        except urllib.error.HTTPError as e:
            if e.code == 404:
                # Model not found on Ollama server
                self._disabled_for_session = True
                self._disable_reason = (
                    f"Model '{self.model}' is not pulled in Ollama. "
                    f"To install it, run: 'ollama pull {self.model}' in your terminal."
                )
                logger.warning(self._disable_reason)
            else:
                logger.warning("Ollama HTTP %d error: %s", e.code, e.reason)
            return None

        except Exception as e:
            self._disabled_for_session = True
            logger.warning("Ollama connection error: %s. Disabling AI mode for this session.", e)
            return None

    # ------------------------------------------------------------------
    # Response parsing
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_response(raw: str) -> Optional[ClassificationResult]:
        """Parse and validate the JSON response from Ollama."""
        json_str = raw.strip()

        start = json_str.find("{")
        end = json_str.rfind("}")
        if start == -1 or end == -1 or end <= start:
            logger.warning("No JSON object found in Ollama response.")
            return None

        json_str = json_str[start : end + 1]

        try:
            data = json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse Ollama JSON: %s", e)
            return None

        is_valid, error, cleaned = validate_json_classification(data)
        if not is_valid or cleaned is None:
            logger.warning("Invalid classification JSON from Ollama: %s", error)
            return None

        return ClassificationResult(
            document_type=cleaned["document_type"],
            category=cleaned["category"],
            subcategory=cleaned["subcategory"],
            topic=cleaned["topic"],
            organization=cleaned["organization"],
            year=cleaned["year"],
            confidence=cleaned["confidence"],
            reason=cleaned["reason"],
            classifier_used="ollama",
        )
