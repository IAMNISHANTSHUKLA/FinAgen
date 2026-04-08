"""
FinAgentX — Retrieval-Time Authorization (Fix #13)

- Filter documents by user role before returning
- Document-level ACLs stored in Weaviate metadata
- Prevents data leakage across organizational boundaries
"""

from __future__ import annotations

import logging

from domain.interfaces import Authorizer
from domain.schemas import RetrievalResult, UserContext

logger = logging.getLogger(__name__)


class RetrievalAuthorizer(Authorizer):
    """
    Enforces access control at retrieval time.

    Documents are tagged with access_roles during ingestion.
    At query time, results are filtered to only include documents
    the user is authorized to see.
    """

    # Tool access by role
    TOOL_PERMISSIONS: dict[str, list[str]] = {
        "analyze_spend": ["analyst", "engineer", "admin"],
        "detect_anomaly": ["analyst", "engineer", "admin"],
        "recommend_action": ["engineer", "admin"],
        "generate_report": ["analyst", "engineer", "admin"],
    }

    def filter_results(
        self,
        results: list[RetrievalResult],
        user_context: UserContext,
    ) -> list[RetrievalResult]:
        """
        Filter retrieval results based on user permissions.

        Checks:
        1. Document access roles match user roles
        2. Ticker restrictions apply
        3. Document type restrictions apply
        """
        if "admin" in user_context.roles:
            return results  # Admins see everything

        filtered = []
        for result in results:
            metadata = result.chunk.metadata

            # Check ticker access
            ticker = metadata.get("ticker", "")
            if (
                user_context.allowed_tickers
                and ticker
                and ticker not in user_context.allowed_tickers
            ):
                continue

            # Check document type access
            doc_type = metadata.get("document_type", "")
            if (
                user_context.allowed_document_types
                and doc_type
                and doc_type not in user_context.allowed_document_types
            ):
                continue

            # Check role-based ACL on document
            access_roles = metadata.get("access_roles", ["public"])
            if isinstance(access_roles, str):
                access_roles = [access_roles]

            if "public" in access_roles or any(
                role in access_roles for role in user_context.roles
            ):
                filtered.append(result)

        removed = len(results) - len(filtered)
        if removed > 0:
            logger.info(
                f"Authorization filtered {removed}/{len(results)} results "
                f"for user {user_context.user_id}",
                extra={
                    "user_id": user_context.user_id,
                    "results_before": len(results),
                    "results_after": len(filtered),
                    "roles": user_context.roles,
                },
            )

        return filtered

    def check_tool_access(
        self,
        tool_name: str,
        user_context: UserContext,
    ) -> bool:
        """Check if user has permission to use a specific tool."""
        if "admin" in user_context.roles:
            return True

        required_roles = self.TOOL_PERMISSIONS.get(tool_name, ["admin"])
        has_access = any(role in required_roles for role in user_context.roles)

        if not has_access:
            logger.warning(
                f"Access denied: user {user_context.user_id} "
                f"cannot use tool '{tool_name}'",
                extra={
                    "user_id": user_context.user_id,
                    "tool_name": tool_name,
                    "user_roles": user_context.roles,
                    "required_roles": required_roles,
                },
            )

        return has_access
