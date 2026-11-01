"""Unified classifier orchestrating the Modular Local AI Strategy (Section 16).

Implements:
- Level A: Deterministic rules, metadata, and lexical matching
- Level B: Semantic embeddings (TF-IDF / multilingual-e5-small) + Specialized Classifiers:
  * ScopeClassifier (Why do I have this document?)
  * WorkRelationshipClassifier (Relationship to organization/project)
  * OrganizationMatcher (Entity registry + alias normalization + fuzzy)
  * DocumentTypeClassifier (Rules + lexical patterns + linear model)
  * DomainClassifier (Independent semantic domain classification)
  * TopicClassifier (Multi-label topic extraction with confidences)
  * ProjectMatcher (Entity & alias retrieval)
- Decision Fusion & Confidence Calibration (Section 16.13, 16.14)
- Level C: Optional Local LLM Fallback (Ollama) for ambiguous/difficult cases
"""

from __future__ import annotations

from typing import Optional

from app.classification.models.embeddings import (
    EmbeddingProvider,
    ModelProfile,
    get_embedding_provider,
)
from app.classification.models.fusion_engine import DecisionFusionEngine
from app.classification.models.specialized_classifiers import (
    DocumentTypeClassifier,
    DomainClassifier,
    OrganizationMatcher,
    ProjectMatcher,
    ScopeClassifier,
    TopicClassifier,
    WorkRelationshipClassifier,
)
from app.classification.ollama_classifier import OllamaClassifier
from app.classification.rule_classifier import RuleClassifier
from app.classification.user_profile import UserProfile, get_default_profile
from app.database.models import (
    ClassificationResult,
    PDFContent,
    PDFFileInfo,
    PDFMetadata,
)
from app.utils.app_logging import get_logger

logger = get_logger("classification")


class Classifier:
    """Unified document classifier implementing Section 16 modular local AI architecture."""

    def __init__(
        self,
        use_ollama: bool = False,
        ollama_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.2",
        user_profile: Optional[UserProfile] = None,
        model_profile: str = ModelProfile.BALANCED,
    ) -> None:
        self.model_profile = model_profile
        self._user_profile: Optional[UserProfile] = user_profile or get_default_profile()
        self._embedding_provider: EmbeddingProvider = get_embedding_provider(profile=model_profile)

        # Specialized Dimension Models (Section 16.3-16.10)
        self.scope_classifier = ScopeClassifier()
        self.work_rel_classifier = WorkRelationshipClassifier()
        self.org_matcher = OrganizationMatcher()
        self.doc_type_classifier = DocumentTypeClassifier()
        self.domain_classifier = DomainClassifier(self._embedding_provider)
        self.topic_classifier = TopicClassifier()
        self.project_matcher = ProjectMatcher()
        self.fusion_engine = DecisionFusionEngine()

        # Deterministic rule engine (Level A)
        self._rule_classifier = RuleClassifier(user_profile=self._user_profile)

        # Optional Local LLM Fallback (Level C)
        self._use_ollama = use_ollama
        self._ollama: Optional[OllamaClassifier] = None
        if use_ollama:
            self._ollama = OllamaClassifier(
                base_url=ollama_url,
                model=ollama_model,
            )

    def set_profile(self, profile: Optional[UserProfile]) -> None:
        """Update active user profile across all components."""
        self._user_profile = profile
        self._rule_classifier.set_profile(profile)

    def set_model_profile(self, profile_name: str) -> None:
        """Switch active model profile (Lightweight, Balanced, Enhanced, Local LLM)."""
        self.model_profile = profile_name
        self._embedding_provider = get_embedding_provider(profile=profile_name)
        self.domain_classifier = DomainClassifier(self._embedding_provider)
        logger.info("Switched model profile to: %s", profile_name)

    @property
    def ollama_available(self) -> bool:
        """Check if Ollama is configured, reachable, and has models installed."""
        if self._ollama is None:
            return False
        return self._ollama.is_available()

    def classify(
        self,
        file_info: PDFFileInfo,
        metadata: Optional[PDFMetadata],
        content: Optional[PDFContent],
    ) -> ClassificationResult:
        """Classify a PDF document using modular decision fusion (Section 16.14)."""
        # Step 1: Run deterministic Rule Engine (Level A)
        rule_res = self._rule_classifier.classify(file_info, metadata, content)

        # Prepare text contexts
        text = content.extracted_text if (content and content.extracted_text) else ""
        filename = file_info.filename
        title = metadata.title if (metadata and metadata.title) else ""
        lead_text = text[:800]
        body_text = text[800:4000]

        # Step 2: Run Specialized Dimension Classifiers (Level B)
        matched_activity = None
        if self._user_profile:
            match_res = self._user_profile.match_activity(text, filename, rule_res.year)
            if match_res:
                matched_activity = match_res[0]

        scope_pred = self.scope_classifier.predict(text, filename, matched_activity)
        work_rel_pred = self.work_rel_classifier.predict(text, filename, matched_activity, rule_res.year)
        org_pred = self.org_matcher.match(text, filename, self._user_profile)
        doc_type_pred = self.doc_type_classifier.predict(filename, title, lead_text, body_text, rule_res.document_type)
        domain_pred = self.domain_classifier.predict(text, filename, self._user_profile)
        topics_pred = self.topic_classifier.predict_multi_label(text, filename)
        project_pred = self.project_matcher.match(text, filename, self._user_profile)

        # Merge with strong rule findings if rule confidence is very high
        if rule_res.confidence >= 0.85:
            if rule_res.category != "Unknown":
                domain_pred.value = rule_res.category
                domain_pred.confidence = max(domain_pred.confidence, rule_res.confidence)
            if rule_res.subcategory != "Unknown":
                topics_pred = [(rule_res.subcategory, rule_res.confidence)] + topics_pred
            if rule_res.organization:
                org_pred.value = rule_res.organization
                org_pred.confidence = max(org_pred.confidence, 0.90)

        # Step 3: Model Decision Fusion (Section 16.14)
        fused_result = self.fusion_engine.fuse(
            scope_pred=scope_pred,
            work_rel_pred=work_rel_pred,
            org_pred=org_pred,
            doc_type_pred=doc_type_pred,
            domain_pred=domain_pred,
            topics_pred=topics_pred,
            project_pred=project_pred,
            year=rule_res.year,
            rule_score=rule_res.confidence,
            classifier_name=f"fusion ({self.model_profile})",
        )

        # Step 4: Optional Local LLM Fallback (Level C - Section 16.22, 16.23)
        # Used only for difficult/ambiguous cases or when Ollama is explicitly requested
        if self._ollama is not None and self._use_ollama:
            if fused_result.needs_review or fused_result.category == "Unknown":
                try:
                    user_domains = [
                        f"{d.category} ({', '.join(d.subcategories[:3])})"
                        for d in self._user_profile.domains
                    ] if (self._user_profile and self._user_profile.domains) else None

                    ai_result = self._ollama.classify(
                        file_info, metadata, content, user_domains=user_domains
                    )
                    if ai_result is not None and ai_result.confidence > fused_result.confidence:
                        ai_result.classifier_used = f"fusion+{self._ollama.model}"
                        return ai_result
                except Exception as e:
                    logger.warning("Ollama fallback failed for %s: %s", file_info.filename, e)

        return fused_result
