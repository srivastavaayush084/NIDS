import asyncio
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
import numpy as np
import pandas as pd

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.database.repository import DetectionResultRepository
from backend.app.ml.registry.model_registry import model_registry
from backend.app.services.ensemble_service import ensemble_service
from backend.app.services.explainer_service import explainer_service
from backend.app.services.alert_service import alert_service
from backend.app.services.lstm_service import lstm_service
from backend.app.detection.engine import detection_engine
from backend.app.schemas.detection import (
    SingleDetectionRequest,
    SingleDetectionResponse,
    BatchDetectionRequest,
    BatchDetectionResponse,
    SequenceDetectionRequest,
    SequenceDetectionResponse,
    DetectionFilterParams,
    ModelPredictionItem,
    ModelAgreementSummary,
    XAIExplanationSummary,
    AlertOutcomeSummary,
    DetectionRequest,
    DetectionResult,
)


class DetectionService:
    """
    Central business logic orchestrator for zero-day attack detection,
    multi-model ensemble inference, Explainable AI (XAI) attributions,
    security alert engine trigger, and MongoDB detection telemetry persistence.
    """

    def __init__(self, repository: Optional[DetectionResultRepository] = None):
        self.repository = repository or DetectionResultRepository()

    async def detect_single(
        self,
        features: Dict[str, Any],
        dataset_name: Optional[str] = "synthetic",
        generate_xai: bool = True,
        flow_context: Optional[Dict[str, Any]] = None,
        persist_db: bool = True,
    ) -> SingleDetectionResponse:
        """
        Execute end-to-end detection on a single network flow event.
        """
        start_time = time.perf_counter()
        ds = dataset_name or "synthetic"
        ctx = flow_context or {}
        now = datetime.now(timezone.utc)
        det_id = f"det-{uuid.uuid4().hex[:12]}"

        # 1. Run Ensemble Inference
        prediction = await ensemble_service.predict_flow_async(
            record=features,
            dataset=ds,
        )

        # 2. Run Explainable AI if requested / configured
        explanation = None
        xai_summary = None
        if generate_xai and settings.XAI_ENABLED:
            try:
                explanation = await explainer_service.explain_record_async(
                    model_name="ensemble",
                    record=features,
                    dataset=ds,
                )
                if explanation:
                    top_feats = []
                    if hasattr(explanation, "fused_feature_contributions"):
                        top_feats = [fc.model_dump() for fc in explanation.fused_feature_contributions[:5]]
                    elif hasattr(explanation, "feature_contributions"):
                        top_feats = [fc.model_dump() for fc in explanation.feature_contributions[:5]]

                    xai_summary = XAIExplanationSummary(
                        is_available=True,
                        explanation_id=getattr(explanation, "explanation_id", None),
                        method="ensemble_risk_attribution",
                        summary=getattr(explanation, "summary", "Feature attributions generated."),
                        top_features=top_feats,
                    )
            except Exception as e:
                logger.warning(f"[{det_id}] XAI explanation calculation failed: {e}")
                xai_summary = XAIExplanationSummary(
                    is_available=False,
                    summary="Explanation calculation encountered an issue.",
                    error=str(e),
                )

        # 3. Pass to Security Alert Engine
        alert_outcome = None
        try:
            alert_res = await alert_service.process_detection_result(
                prediction=prediction,
                flow_context=ctx,
                explanation=explanation,
                detection_result_id=det_id,
            )
            alert_outcome = AlertOutcomeSummary(
                created=alert_res.alert_created,
                alert_id=alert_res.alert_id,
                deduplicated=alert_res.deduplicated,
                occurrence_count=alert_res.occurrence_count,
                severity=alert_res.severity,
                priority=alert_res.priority,
                status=alert_res.status,
                reason=alert_res.reason,
            )
        except Exception as e:
            logger.error(f"[{det_id}] Alert processing error: {e}", exc_info=True)
            alert_outcome = AlertOutcomeSummary(
                created=False,
                reason=f"Alert engine error: {str(e)}",
            )

        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        # 4. Assemble Model Prediction Breakdown
        model_items: List[ModelPredictionItem] = []
        for m_name, c in prediction.contributions.items():
            model_items.append(
                ModelPredictionItem(
                    name=m_name,
                    prediction=c.prediction,
                    is_anomaly=c.is_anomaly,
                    native_score=round(c.native_score, 4),
                    normalized_score=round(c.normalized_score, 2),
                    weight=round(c.effective_weight, 4),
                    weighted_contribution=round(c.effective_weight * c.normalized_score, 2),
                    latency_ms=round(c.latency_ms, 3),
                    is_available=c.is_available,
                    error=c.error,
                )
            )

        agreement_summary = ModelAgreementSummary(
            models_total=prediction.agreement.models_total,
            models_available=prediction.agreement.models_available,
            models_anomalous=prediction.agreement.models_anomalous,
            models_normal=prediction.agreement.models_normal,
            agreement_ratio=round(prediction.agreement.agreement_ratio, 4),
            consensus_prediction=prediction.agreement.consensus_prediction,
        )

        response_obj = SingleDetectionResponse(
            detection_id=det_id,
            timestamp=now,
            dataset_name=ds,
            prediction=prediction.prediction,
            is_anomaly=prediction.is_anomaly,
            risk_score=round(prediction.risk_score, 2),
            severity=prediction.severity,
            threshold=prediction.decision_threshold,
            model_agreement=agreement_summary,
            models=model_items,
            explanation=xai_summary,
            alert=alert_outcome,
            flow_context=ctx,
            processing_time_ms=round(elapsed_ms, 2),
        )

        # 5. Persist Detection Result Document (if enabled)
        if persist_db:
            try:
                doc = response_obj.model_dump()
                doc["_id"] = det_id
                await self.repository.insert_one(doc)
            except Exception as e:
                logger.warning(f"[{det_id}] Could not persist detection result to DB: {e}")

        return response_obj

    async def detect_batch(
        self,
        events: List[Dict[str, Any]],
        dataset_name: Optional[str] = "synthetic",
        generate_xai: bool = False,
    ) -> BatchDetectionResponse:
        """
        Execute batch detection across multiple network flow events with rate and batch limit enforcement.
        Uses vectorized multi-model batch ensemble inference and single bulk persistence.
        """
        start_time = time.perf_counter()
        ds = dataset_name or "synthetic"
        now = datetime.now(timezone.utc)

        if len(events) > settings.MAX_DETECTION_BATCH_SIZE:
            raise ValueError(
                f"Batch size {len(events)} exceeds maximum allowed limit ({settings.MAX_DETECTION_BATCH_SIZE})."
            )

        if not events:
            return BatchDetectionResponse(
                total=0,
                successful=0,
                failed=0,
                anomalies=0,
                alerts_created=0,
                processing_time_ms=0.0,
                results=[],
                errors=[],
            )

        # 1. Extract feature dictionaries and flow contexts
        feature_list: List[Dict[str, Any]] = []
        contexts: List[Dict[str, Any]] = []
        for ev in events:
            if isinstance(ev, dict):
                feats = ev.get("features", ev)
                ctx = {
                    "source_ip": ev.get("source_ip"),
                    "destination_ip": ev.get("destination_ip"),
                    "source_port": ev.get("source_port"),
                    "destination_port": ev.get("destination_port"),
                    "protocol": ev.get("protocol", "TCP"),
                }
            else:
                feats = {}
                ctx = {}
            feature_list.append(feats)
            contexts.append(ctx)

        # 2. Vectorized Batch Ensemble Inference
        detector = ensemble_service.get_detector(ds)
        _, _, pred_objs = await asyncio.to_thread(detector.predict_batch, feature_list)

        results: List[SingleDetectionResponse] = []
        errors: List[Dict[str, Any]] = []
        docs_to_persist: List[Dict[str, Any]] = []
        anomalies_count = 0
        alerts_count = 0

        # 3. Assemble Responses
        for i, (pred, feats, ctx) in enumerate(zip(pred_objs, feature_list, contexts)):
            det_id = f"det-batch-{uuid.uuid4().hex[:10]}-{i}"
            xai_summary = None
            if generate_xai and settings.XAI_ENABLED:
                try:
                    explanation = await explainer_service.explain_record_async(
                        model_name="ensemble",
                        record=feats,
                        dataset=ds,
                    )
                    if explanation:
                        top_feats = []
                        if hasattr(explanation, "fused_feature_contributions"):
                            top_feats = [fc.model_dump() for fc in explanation.fused_feature_contributions[:5]]
                        elif hasattr(explanation, "feature_contributions"):
                            top_feats = [fc.model_dump() for fc in explanation.feature_contributions[:5]]
                        xai_summary = XAIExplanationSummary(
                            is_available=True,
                            explanation_id=getattr(explanation, "explanation_id", None),
                            method="ensemble_risk_attribution",
                            summary=getattr(explanation, "summary", "Feature attributions generated."),
                            top_features=top_feats,
                        )
                except Exception as e:
                    logger.warning(f"Batch XAI attribution error on item {i}: {e}")

            model_items: List[ModelPredictionItem] = []
            for m_name, c in pred.contributions.items():
                model_items.append(
                    ModelPredictionItem(
                        name=m_name,
                        prediction=c.prediction,
                        is_anomaly=c.is_anomaly,
                        native_score=round(c.native_score, 4),
                        normalized_score=round(c.normalized_score, 2),
                        weight=round(c.effective_weight, 4),
                        weighted_contribution=round(c.effective_weight * c.normalized_score, 2),
                        latency_ms=round(c.latency_ms, 3),
                        is_available=c.is_available,
                        error=c.error,
                    )
                )

            agreement_summary = ModelAgreementSummary(
                models_total=pred.agreement.models_total,
                models_available=pred.agreement.models_available,
                models_anomalous=pred.agreement.models_anomalous,
                models_normal=pred.agreement.models_normal,
                agreement_ratio=round(pred.agreement.agreement_ratio, 4),
                consensus_prediction=pred.agreement.consensus_prediction,
            )

            res_obj = SingleDetectionResponse(
                detection_id=det_id,
                timestamp=now,
                dataset_name=ds,
                prediction=pred.prediction,
                is_anomaly=pred.is_anomaly,
                risk_score=round(pred.risk_score, 2),
                severity=pred.severity,
                threshold=pred.decision_threshold,
                model_agreement=agreement_summary,
                models=model_items,
                explanation=xai_summary,
                alert=None,
                flow_context=ctx,
                processing_time_ms=round(pred.latency.total_ms, 2),
            )

            if pred.is_anomaly:
                anomalies_count += 1

            results.append(res_obj)
            doc = res_obj.model_dump()
            doc["_id"] = det_id
            docs_to_persist.append(doc)

        # 4. Bulk Persist in Single Roundtrip
        if docs_to_persist:
            try:
                await self.repository.insert_many(docs_to_persist)
            except Exception as e:
                logger.warning(f"Batch detection bulk insert error: {e}")

        total_ms = (time.perf_counter() - start_time) * 1000.0

        return BatchDetectionResponse(
            total=len(events),
            successful=len(results),
            failed=len(errors),
            anomalies=anomalies_count,
            alerts_created=alerts_count,
            processing_time_ms=round(total_ms, 2),
            results=results,
            errors=errors,
        )

    async def detect_sequence(
        self,
        sequence: List[Dict[str, Any]],
        dataset_name: Optional[str] = "synthetic",
        generate_xai: bool = True,
        flow_context: Optional[Dict[str, Any]] = None,
    ) -> SequenceDetectionResponse:
        """
        Execute temporal sequence-level anomaly detection using the LSTM Autoencoder engine.
        """
        start_time = time.perf_counter()
        ds = dataset_name or "synthetic"
        ctx = flow_context or {}
        now = datetime.now(timezone.utc)
        det_id = f"det-seq-{uuid.uuid4().hex[:12]}"

        if len(sequence) < 2:
            raise ValueError("Sequence detection requires at least 2 consecutive time-ordered records.")
        if len(sequence) > settings.MAX_SEQUENCE_LENGTH:
            raise ValueError(
                f"Sequence length {len(sequence)} exceeds maximum allowed limit ({settings.MAX_SEQUENCE_LENGTH})."
            )

        # Convert list of dicts to 2D numpy array if needed
        if sequence and isinstance(sequence[0], dict):
            meta = model_registry.get_model("lstm_autoencoder", dataset=ds)
            feat_names = meta.get("feature_names", []) if meta else []
            if feat_names and any(k in sequence[0] for k in feat_names):
                seq_matrix = np.array([[float(row.get(k, 0.0)) for k in feat_names] for row in sequence], dtype=np.float32)
            else:
                seq_matrix = np.array([list(row.values()) for row in sequence], dtype=np.float32)
        else:
            seq_matrix = np.asarray(sequence, dtype=np.float32)

        # Run LSTM sequential detection
        seq_result = await lstm_service.predict_sequence_async(
            sequence=seq_matrix,
            dataset=ds,
        )

        # Run temporal timestep explainability
        xai_summary = None
        peak_t = None
        if generate_xai and settings.XAI_ENABLED:
            try:
                explanation = await explainer_service.explain_record_async(
                    model_name="lstm",
                    record=seq_matrix,
                    dataset=ds,
                )
                if explanation and hasattr(explanation, "timestep_contributions") and explanation.timestep_contributions:
                    peak_t = explanation.timestep_contributions[0].timestep_label
                    xai_summary = XAIExplanationSummary(
                        is_available=True,
                        explanation_id=explanation.explanation_id,
                        method="lstm_hierarchical_reconstruction",
                        summary=explanation.summary,
                        peak_timestep=peak_t,
                        top_features=[fc.model_dump() for fc in explanation.feature_contributions[:5]],
                    )
            except Exception as e:
                logger.warning(f"[{det_id}] Sequence XAI calculation error: {e}")

        # Map risk score to threat severity
        risk = float(getattr(seq_result, "anomaly_score", getattr(seq_result, "risk_score", 0.0)))
        if risk >= 75.0:
            severity = "CRITICAL"
        elif risk >= 50.0:
            severity = "HIGH"
        elif risk >= 25.0:
            severity = "MEDIUM"
        else:
            severity = "LOW"

        raw_err = float(getattr(seq_result, "raw_score", getattr(seq_result, "reconstruction_error", 0.0)))
        th = float(getattr(seq_result, "threshold", 0.5))
        pred_label = getattr(seq_result, "prediction", "normal")
        is_anom = bool(getattr(seq_result, "is_anomaly", False))

        total_ms = (time.perf_counter() - start_time) * 1000.0

        resp = SequenceDetectionResponse(
            detection_id=det_id,
            detection_type="sequence_detection",
            timestamp=now,
            dataset_name=ds,
            prediction=pred_label,
            is_anomaly=is_anom,
            risk_score=round(risk, 2),
            severity=severity,
            reconstruction_error=round(raw_err, 6),
            threshold=round(th, 6),
            sequence_length=len(sequence),
            peak_anomalous_timestep=peak_t,
            explanation=xai_summary,
            processing_time_ms=round(total_ms, 2),
        )

        # Persist sequence detection result
        try:
            doc = resp.model_dump()
            doc["_id"] = det_id
            await self.repository.insert_one(doc)
        except Exception as e:
            logger.warning(f"[{det_id}] Could not persist sequence detection to DB: {e}")

        return resp

    async def get_detection(self, detection_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve historical detection result document by detection_id or _id."""
        return await self.repository.find_by_detection_id(detection_id)

    async def query_detections(
        self,
        params: Optional[DetectionFilterParams] = None,
    ) -> Dict[str, Any]:
        """Query detection history with filtering and pagination."""
        p = params or DetectionFilterParams()
        query: Dict[str, Any] = {}

        if p.severity:
            query["severity"] = p.severity.upper()
        if p.prediction:
            query["prediction"] = p.prediction.lower()
        if p.is_anomaly is not None:
            query["is_anomaly"] = p.is_anomaly
        if p.dataset_name:
            query["dataset_name"] = p.dataset_name
        if p.min_risk_score is not None:
            query["risk_score"] = {"$gte": p.min_risk_score}
        if p.start_time or p.end_time:
            time_filter: Dict[str, Any] = {}
            if p.start_time:
                time_filter["$gte"] = p.start_time
            if p.end_time:
                time_filter["$lte"] = p.end_time
            query["timestamp"] = time_filter

        limit = min(p.page_size, settings.MAX_PAGE_SIZE)
        skip = (p.page - 1) * limit

        docs = await self.repository.query_detections(query, limit=limit, skip=skip)
        total = await self.repository.count(query)
        total_pages = (total + limit - 1) // limit if limit > 0 else 1

        return {
            "total": total,
            "page": p.page,
            "page_size": limit,
            "total_pages": total_pages,
            "items": docs,
        }

    # =========================================================================
    # Backwards Compatibility API Layer (Phases 1-2)
    # =========================================================================
    async def run_detection(self, request: DetectionRequest) -> DetectionResult:
        """Legacy helper for single flow analysis."""
        return await detection_engine.analyze_flow(
            flow=request.flow,
            active_models=request.active_models,
        )

    async def run_batch_detection(self, request: Any) -> Any:
        """Legacy helper for batch flow analysis."""
        results: List[DetectionResult] = []
        anomalies = 0
        high_risk = 0

        for flow in request.flows:
            res = await detection_engine.analyze_flow(flow, getattr(request, "active_models", None))
            if res.is_zero_day_suspect:
                anomalies += 1
            if res.risk_score >= 0.85:
                high_risk += 1
            results.append(res)

        from backend.app.schemas.detection import BatchDetectionResponse as LegacyBatchResponse
        return LegacyBatchResponse(
            total_analyzed=len(request.flows),
            anomalies_detected=anomalies,
            high_risk_count=high_risk,
            results=results,
        )


detection_service = DetectionService()
