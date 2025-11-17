"""
Scheme Sharing Routes

Handles sharing marking schemes with users and groups with configurable permissions.
Implements User Story 5 (Share with Users) and User Story 6 (Share with Groups).
Web version only.
"""

from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
import json
from datetime import datetime

scheme_sharing_bp = Blueprint('scheme_sharing', __name__, url_prefix='/api/schemes')


@scheme_sharing_bp.route('/<scheme_id>/share', methods=['POST'])
@login_required
def share_scheme(scheme_id):
    """
    Grant access to a marking scheme with specified permissions.

    POST /schemes/{id}/share
    - Verify user is owner (403 if not)
    - Accept array of recipients: [{type: "user", user_id: "..."}, {type: "group", group_id: "..."}]
    - Accept permission: VIEW_ONLY, EDITABLE, or COPY
    - For each recipient:
      1. Create SchemeShare record
      2. Set shared_by_id = current user
      3. Set shared_at = now()
      4. Verify recipient exists (404 if not)
    - Return 200 with shares_created count
    - Emit notification events (FR-018)

    Response:
        200: {shares_created: int}
        403: not owner
        404: recipient not found
        422: invalid permission
    """
    # TODO: Implement share endpoint (T118)
    pass


@scheme_sharing_bp.route('/<scheme_id>/share/<share_id>/revoke', methods=['DELETE'])
@login_required
def revoke_share(scheme_id, share_id):
    """
    Revoke access to a marking scheme.

    DELETE /schemes/{id}/share/{share_id}/revoke
    - Verify user is owner (403 if not)
    - Retrieve SchemeShare record
    - Set revoked_at = now()
    - Set revoked_by_id = current user
    - Save to database

    Response:
        204: No Content
        403: not owner
        404: share not found
    """
    # TODO: Implement revoke endpoint (T119)
    pass


@scheme_sharing_bp.route('/<scheme_id>/shares', methods=['GET'])
@login_required
def list_shares(scheme_id):
    """
    List all shares for a marking scheme (active and revoked).

    GET /schemes/{id}/shares
    - Verify user is owner (403 if not)
    - Query all SchemeShare records for scheme_id
    - Include all shares (both active and revoked, or filter by revoked_at)
    - Return array of: {share_id, user_id/group_id, permission, shared_at, revoked_at, shared_by}

    Response:
        200: [{share_id, user_id/group_id, permission, shared_at, revoked_at, shared_by}]
        403: not owner
        404: scheme not found
    """
    # TODO: Implement list shares endpoint (T120)
    pass


@scheme_sharing_bp.route('/shared-with-me', methods=['GET'])
@login_required
def list_shared_schemes():
    """
    List all schemes shared with current user or their groups.

    GET /schemes/shared-with-me
    - Use permission_checker.get_user_accessible_schemes()
    - Filter by current user
    - Optional query param: permission_filter (VIEW_ONLY, EDITABLE, COPY)
    - Return array of: {scheme_id, name, owner, permission, shared_at, shared_by, criteria_count}

    Response:
        200: [{scheme_id, name, owner, permission, shared_at, shared_by, criteria_count}]
    """
    # TODO: Implement shared-with-me endpoint (T121)
    pass
