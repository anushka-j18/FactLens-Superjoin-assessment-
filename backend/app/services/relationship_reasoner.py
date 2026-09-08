import uuid
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.entities import Document, Fact, FactRelationship
from app.services.normalizer import FactNormalizer


class RelationshipReasonerError(Exception):
    pass


class RelationshipReasonerService:
    """Core reasoning engine classifying cross-document fact relationships into 4 mandatory cases:
    
    1. CORROBORATED
    2. CONTRADICTED
    3. CONTEXTUALLY_RECONCILED
    4. REASONING_FAILURE
    """

    @classmethod
    def analyze_cross_document_relationships(
        cls,
        db: Session,
        document_ids: Optional[List[str]] = None
    ) -> List[FactRelationship]:
        """Generate candidate pairs across distinct documents and evaluate 4-case relationships."""
        query = db.query(Fact).filter(Fact.extraction_status == "grounded")
        if document_ids:
            query = query.filter(Fact.document_id.in_(document_ids))

        facts = query.all()
        if len(facts) < 2:
            return []

        # Delete existing relationships for the target set of facts
        fact_ids = [f.id for f in facts]
        db.query(FactRelationship).filter(
            FactRelationship.source_fact_id.in_(fact_ids)
        ).delete(synchronize_session=False)
        db.commit()

        created_relationships: List[FactRelationship] = []
        seen_pairs = set()

        # Pairwise comparison across distinct documents
        for i in range(len(facts)):
            for j in range(i + 1, len(facts)):
                f1 = facts[i]
                f2 = facts[j]

                # Only compare facts from distinct documents
                if f1.document_id == f2.document_id:
                    continue

                pair_key = tuple(sorted([f1.id, f2.id]))
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                # Check comparability
                dict1 = cls._fact_to_dict(f1)
                dict2 = cls._fact_to_dict(f2)

                comp = FactNormalizer.are_facts_comparable(dict1, dict2)

                # Evaluate relationship if facts share subject & predicate
                if comp["is_comparable"]:
                    rel = cls._classify_fact_pair(db, f1, f2, comp)
                    if rel:
                        db.add(rel)
                        created_relationships.append(rel)

        db.commit()

        for rel in created_relationships:
            db.refresh(rel)

        return created_relationships

    @classmethod
    def _classify_fact_pair(
        cls,
        db: Session,
        f1: Fact,
        f2: Fact,
        comp: Dict[str, Any]
    ) -> Optional[FactRelationship]:
        """Classify pair of facts into 1 of the 4 mandatory categories."""

        # Check values equivalence
        val1 = f1.normalized_value if f1.normalized_value is not None else f1.value.strip()
        val2 = f2.normalized_value if f2.normalized_value is not None else f2.value.strip()

        values_match = False
        if isinstance(val1, float) and isinstance(val2, float):
            # Check relative/absolute float tolerance
            values_match = abs(val1 - val2) < 1e-3 or (val1 == 0 and val2 == 0)
        else:
            values_match = str(val1).lower() == str(val2).lower()

        temp_match = comp["temporal_match"]
        geo_match = comp["geographic_match"]
        scope1 = f1.operating_scope.strip().lower() if f1.operating_scope else ""
        scope2 = f2.operating_scope.strip().lower() if f2.operating_scope else ""
        scope_match = (scope1 == scope2) if (scope1 and scope2) else None

        # Check for Extraction/Reasoning Failure
        if f1.extraction_status != "grounded" or f2.extraction_status != "grounded" or f1.extraction_confidence < 0.5 or f2.extraction_confidence < 0.5:
            return FactRelationship(
                id=str(uuid.uuid4()),
                source_fact_id=f1.id,
                target_fact_id=f2.id,
                relationship_type="REASONING_FAILURE",
                confidence_score=0.40,
                reasoning_summary=f"Extraction / Reasoning Failure [insufficient_context]: Source or target evidence confidence is below verification threshold.",
                reconciliation_context={
                    "reason": "insufficient_context",
                    "failure_reason": "insufficient_context",
                    "confidence_level": "LOW",
                    "needs_review": True
                },
            )

        # 1. CORROBORATED
        if values_match and (temp_match in [True, None]) and (geo_match in [True, None]) and (scope_match in [True, None]):
            timeframe_str = f1.temporal_context or "the reported period"
            return FactRelationship(
                id=str(uuid.uuid4()),
                source_fact_id=f1.id,
                target_fact_id=f2.id,
                relationship_type="CORROBORATED",
                confidence_score=0.95,
                reasoning_summary=f"Corroborated: Document '{f1.document.original_filename}' and Document '{f2.document.original_filename}' consistently report {f1.predicate} as '{f1.value}' for {timeframe_str}.",
                reconciliation_context={
                    "matched_predicate": f1.predicate,
                    "matched_value": f1.value,
                    "temporal_context": f1.temporal_context,
                    "confidence_level": "HIGH",
                    "needs_review": False
                },
            )

        # 2. CONTRADICTED / LIKELY CONTRADICTION
        if not values_match and (temp_match in [True, None]) and (geo_match in [True, None]) and (scope_match in [True, None]):
            timeframe_str = f1.temporal_context or "the same timeframe"
            return FactRelationship(
                id=str(uuid.uuid4()),
                source_fact_id=f1.id,
                target_fact_id=f2.id,
                relationship_type="CONTRADICTED",
                confidence_score=0.90,
                reasoning_summary=f"Contradicted: Document '{f1.document.original_filename}' states {f1.predicate} was '{f1.value}' while Document '{f2.document.original_filename}' states '{f2.value}' for {timeframe_str}.",
                reconciliation_context={
                    "conflict_type": "value_mismatch",
                    "source_value": f1.value,
                    "target_value": f2.value,
                    "temporal_context": f1.temporal_context,
                    "confidence_level": "HIGH",
                    "needs_review": False
                },
            )

        # 3. CONTEXTUALLY RECONCILED
        if (temp_match is False) or (geo_match is False) or (scope_match is False) or (f1.currency and f2.currency and f1.currency != f2.currency):
            reasons = []
            failure_reason = None
            if temp_match is False:
                reasons.append(f"timeframe difference ({f1.temporal_context} vs {f2.temporal_context})")
                failure_reason = "conflicting_temporal_information"
            if geo_match is False:
                reasons.append(f"geographic scope difference ({f1.geographic_scope} vs {f2.geographic_scope})")
                if not failure_reason:
                    failure_reason = "ambiguous_scope"
            if scope_match is False:
                reasons.append(f"operating scope difference ({f1.operating_scope} vs {f2.operating_scope})")
                if not failure_reason:
                    failure_reason = "ambiguous_scope"
            if f1.currency and f2.currency and f1.currency != f2.currency:
                reasons.append(f"currency difference ({f1.currency} vs {f2.currency})")

            reason_str = ", ".join(reasons) if reasons else "contextual variation"

            return FactRelationship(
                id=str(uuid.uuid4()),
                source_fact_id=f1.id,
                target_fact_id=f2.id,
                relationship_type="CONTEXTUALLY_RECONCILED",
                confidence_score=0.88,
                reasoning_summary=f"Contextually Reconciled: Surface difference between '{f1.value}' and '{f2.value}' is explained by {reason_str}.",
                reconciliation_context={
                    "reconciliation_reasons": reasons,
                    "source_context": {"temporal": f1.temporal_context, "geo": f1.geographic_scope, "currency": f1.currency},
                    "target_context": {"temporal": f2.temporal_context, "geo": f2.geographic_scope, "currency": f2.currency},
                    "confidence_level": "HIGH",
                    "needs_review": False
                },
            )

        # Fallback to REASONING_FAILURE if ambiguous
        return FactRelationship(
            id=str(uuid.uuid4()),
            source_fact_id=f1.id,
            target_fact_id=f2.id,
            relationship_type="REASONING_FAILURE",
            confidence_score=0.45,
            reasoning_summary=f"Extraction / Reasoning Failure [insufficient_context]: Unable to conclusively reconcile values '{f1.value}' and '{f2.value}' due to ambiguous context.",
            reconciliation_context={
                "reason": "ambiguous_context",
                "failure_reason": "insufficient_context",
                "confidence_level": "LOW",
                "needs_review": True
            },
        )

    @staticmethod
    def _fact_to_dict(fact: Fact) -> Dict[str, Any]:
        return {
            "subject": fact.subject,
            "predicate": fact.predicate,
            "value": fact.value,
            "normalized_value": fact.normalized_value,
            "unit": fact.unit,
            "currency": fact.currency,
            "temporal_context": fact.temporal_context,
            "geographic_scope": fact.geographic_scope,
            "operating_scope": fact.operating_scope,
        }
