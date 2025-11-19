"""
Scheme Sharing Routes

Handles sharing marking schemes with users and groups with configurable permissions.
Implements User Story 5 (Share with Users) and User Story 6 (Share with Groups).
Web version only.
"""

from flask import Blueprint, request, jsonify, current_app
from datetime import datetime, timezone
from models import db, GradingScheme, MarkingScheme, SchemeShare, SharePermission, User
from services.permission_checker import PermissionChecker

scheme_sharing_bp = Blueprint('scheme_sharing', __name__, url_prefix='/api/schemes')


def get_current_user_id():
    """
    Get current user ID from session.

    In tests, this uses session['user_id'].
    In production with flask-login, would use current_user.id.
    """
    from flask import session
    try:
        from flask_login import current_user
        if hasattr(current_user, 'id'):
            return current_user.id
    except (ImportError, AttributeError):
        pass

    # Fallback to session for testing
    return session.get('user_id')


def notify_scheme_shared(recipient_id: str, scheme_name: str, shared_by_email: str, permission: str):
    """
    Send notification when scheme is shared (T124).

    Placeholder for actual notification system.
    Can be extended to:
    - Create Notification record
    - Queue email
    - Send push notification

    Args:
        recipient_id: User ID of recipient
        scheme_name: Name of shared scheme
        shared_by_email: Email of user who shared
        permission: Permission level granted
    """
    # Log for audit trail
    current_app.logger.info(
        f"[SHARING] Scheme '{scheme_name}' shared with user {recipient_id} "
        f"by {shared_by_email} with permission {permission}"
    )
    # TODO: Implement actual notification system when ready


def log_sharing_action(action: str, scheme_id: str, user_id: str, **kwargs):
    """
    Log sharing actions for audit trail (T125).

    Args:
        action: Action type (SHARE_GRANTED, SHARE_REVOKED, etc.)
        scheme_id: Scheme ID
        user_id: User ID performing action
        **kwargs: Additional metadata
    """
    current_app.logger.info(
        f"[AUDIT] {action} - Scheme: {scheme_id}, User: {user_id}, "
        f"Details: {kwargs}"
    )
    # TODO: Store in DocumentUploadLog or dedicated audit table when ready


@scheme_sharing_bp.route('/<scheme_id>/share', methods=['POST'])
def share_scheme(scheme_id):
    """
    Grant access to a marking scheme with specified permissions (T118).

    POST /api/schemes/{id}/share

    Request body:
    {
        "user_id": "uuid",  # Either user_id or group_id (XOR)
        "group_id": "uuid",
        "permission": "VIEW_ONLY" | "EDITABLE" | "COPY"
    }

    Response:
        201: Share created successfully
        400: Invalid request (missing fields, both user_id and group_id, etc.)
        403: User is not owner
        404: Scheme or recipient not found
        409: Share already exists
    """
    try:
        current_user_id = get_current_user_id()
        if not current_user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Check if scheme exists
        scheme = GradingScheme.query.filter_by(id=scheme_id).first()
        if not scheme:
            # Try MarkingScheme
            scheme = MarkingScheme.query.filter_by(id=scheme_id).first()
            if not scheme:
                return jsonify({"error": "Scheme not found"}), 404

        # Verify user is owner
        if hasattr(scheme, 'created_by') and scheme.created_by != current_user_id:
            return jsonify({"error": "Only scheme owner can share"}), 403

        # Force JSON parsing
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.get_json(force=True, silent=False)
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        # Validate permission
        permission = data.get('permission')
        if not permission:
            return jsonify({"error": "permission is required"}), 400

        valid_permissions = [p.value for p in SharePermission]
        if permission not in valid_permissions:
            return jsonify({"error": f"Invalid permission. Must be one of: {', '.join(valid_permissions)}"}), 400

        # Validate XOR constraint (either user_id or group_id, not both)
        user_id = data.get('user_id')
        group_id = data.get('group_id')

        if user_id and group_id:
            return jsonify({"error": "Provide either user_id or group_id, not both"}), 400

        if not user_id and not group_id:
            return jsonify({"error": "Either user_id or group_id is required"}), 400

        # Verify recipient exists (if user_id)
        if user_id:
            recipient = User.query.filter_by(id=user_id).first()
            if not recipient:
                return jsonify({"error": "Recipient user not found"}), 404

            # Check for existing share
            existing_share = SchemeShare.query.filter_by(
                scheme_id=scheme_id,
                user_id=user_id
            ).filter(
                SchemeShare.revoked_at.is_(None)
            ).first()

            if existing_share:
                return jsonify({"error": "Scheme already shared with this user"}), 409

        # Check for existing group share
        if group_id:
            existing_share = SchemeShare.query.filter_by(
                scheme_id=scheme_id,
                group_id=group_id
            ).filter(
                SchemeShare.revoked_at.is_(None)
            ).first()

            if existing_share:
                return jsonify({"error": "Scheme already shared with this group"}), 409

        # Create share
        share = SchemeShare(
            scheme_id=scheme_id,
            user_id=user_id,
            group_id=group_id,
            permission=permission,
            shared_by_id=current_user_id,
            shared_at=datetime.now(timezone.utc)
        )

        db.session.add(share)
        db.session.commit()

        # Log action
        log_sharing_action(
            "SHARE_GRANTED",
            scheme_id,
            current_user_id,
            recipient_user_id=user_id,
            recipient_group_id=group_id,
            permission=permission
        )

        # Send notification
        if user_id:
            current_user = User.query.filter_by(id=current_user_id).first()
            notify_scheme_shared(
                user_id,
                scheme.name,
                current_user.email if current_user else "Unknown",
                permission
            )

        return jsonify(share.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error sharing scheme: {str(e)}")
        return jsonify({"error": str(e)}), 500


@scheme_sharing_bp.route('/<scheme_id>/share/bulk', methods=['POST'])
def bulk_share_scheme(scheme_id):
    """
    Share scheme with multiple recipients in a single request (T114).

    POST /api/schemes/{id}/share/bulk

    Request body:
    {
        "user_ids": ["uuid1", "uuid2", ...],  # Either user_ids or group_ids
        "group_ids": ["group1", "group2", ...],
        "permission": "VIEW_ONLY" | "EDITABLE" | "COPY"
    }

    Response:
        201: All shares created
        207: Partial success (multi-status)
        400: Invalid request
        403: Not owner
    """
    try:
        current_user_id = get_current_user_id()
        if not current_user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Check if scheme exists
        scheme = GradingScheme.query.filter_by(id=scheme_id).first()
        if not scheme:
            scheme = MarkingScheme.query.filter_by(id=scheme_id).first()
            if not scheme:
                return jsonify({"error": "Scheme not found"}), 404

        # Verify user is owner
        if hasattr(scheme, 'created_by') and scheme.created_by != current_user_id:
            return jsonify({"error": "Only scheme owner can share"}), 403

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body is required"}), 400

        permission = data.get('permission')
        if not permission:
            return jsonify({"error": "permission is required"}), 400

        valid_permissions = [p.value for p in SharePermission]
        if permission not in valid_permissions:
            return jsonify({"error": f"Invalid permission. Must be one of: {', '.join(valid_permissions)}"}), 400

        user_ids = data.get('user_ids', [])
        group_ids = data.get('group_ids', [])

        # Enforce reasonable limit (1000 recipients)
        total_recipients = len(user_ids) + len(group_ids)
        if total_recipients > 1000:
            return jsonify({"error": "Too many recipients. Maximum 1000 allowed."}), 400

        if total_recipients == 0:
            return jsonify({"error": "No recipients provided"}), 400

        shares_created = 0
        shares_skipped = 0
        errors = []
        created_shares = []

        # Process user shares
        for user_id in user_ids:
            try:
                # Verify user exists
                recipient = User.query.filter_by(id=user_id).first()
                if not recipient:
                    errors.append({"user_id": user_id, "error": "User not found"})
                    continue

                # Check for existing share
                existing_share = SchemeShare.query.filter_by(
                    scheme_id=scheme_id,
                    user_id=user_id
                ).filter(
                    SchemeShare.revoked_at.is_(None)
                ).first()

                if existing_share:
                    shares_skipped += 1
                    errors.append({"user_id": user_id, "error": "Already shared"})
                    continue

                # Create share
                share = SchemeShare(
                    scheme_id=scheme_id,
                    user_id=user_id,
                    permission=permission,
                    shared_by_id=current_user_id,
                    shared_at=datetime.now(timezone.utc)
                )
                db.session.add(share)
                db.session.flush()

                created_shares.append(share.to_dict())
                shares_created += 1

            except Exception as e:
                errors.append({"user_id": user_id, "error": str(e)})

        # Process group shares
        for group_id in group_ids:
            try:
                # Check for existing share
                existing_share = SchemeShare.query.filter_by(
                    scheme_id=scheme_id,
                    group_id=group_id
                ).filter(
                    SchemeShare.revoked_at.is_(None)
                ).first()

                if existing_share:
                    shares_skipped += 1
                    errors.append({"group_id": group_id, "error": "Already shared"})
                    continue

                # Create share
                share = SchemeShare(
                    scheme_id=scheme_id,
                    group_id=group_id,
                    permission=permission,
                    shared_by_id=current_user_id,
                    shared_at=datetime.now(timezone.utc)
                )
                db.session.add(share)
                db.session.flush()

                created_shares.append(share.to_dict())
                shares_created += 1

            except Exception as e:
                errors.append({"group_id": group_id, "error": str(e)})

        db.session.commit()

        # Log bulk action
        log_sharing_action(
            "BULK_SHARE_GRANTED",
            scheme_id,
            current_user_id,
            shares_created=shares_created,
            shares_skipped=shares_skipped,
            errors_count=len(errors)
        )

        # Return appropriate status code
        if shares_created > 0 and len(errors) == 0:
            # All succeeded
            return jsonify({
                "shares_created": shares_created,
                "shares": created_shares
            }), 201
        elif shares_created > 0:
            # Partial success
            return jsonify({
                "shares_created": shares_created,
                "shares_skipped": shares_skipped,
                "shares": created_shares,
                "errors": errors
            }), 207
        else:
            # All failed
            return jsonify({
                "shares_created": 0,
                "errors": errors
            }), 207

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error in bulk share: {str(e)}")
        return jsonify({"error": str(e)}), 500


@scheme_sharing_bp.route('/shares/<share_id>', methods=['DELETE'])
def revoke_share(share_id):
    """
    Revoke access to a marking scheme (T119).

    DELETE /api/schemes/shares/{id}

    Response:
        204: Share revoked successfully
        403: User is not owner
        404: Share not found
        409: Share already revoked
    """
    try:
        current_user_id = get_current_user_id()
        if not current_user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Get share
        share = SchemeShare.query.filter_by(id=share_id).first()
        if not share:
            return jsonify({"error": "Share not found"}), 404

        # Check if already revoked
        if share.revoked_at is not None:
            return jsonify({"error": "Share already revoked"}), 409

        # Verify user is owner of scheme
        scheme = GradingScheme.query.filter_by(id=share.scheme_id).first()
        if not scheme:
            scheme = MarkingScheme.query.filter_by(id=share.scheme_id).first()

        if scheme and hasattr(scheme, 'created_by') and scheme.created_by != current_user_id:
            return jsonify({"error": "Only scheme owner can revoke shares"}), 403

        # Revoke share
        share.revoked_at = datetime.now(timezone.utc)
        share.revoked_by_id = current_user_id

        db.session.commit()

        # Log action
        log_sharing_action(
            "SHARE_REVOKED",
            share.scheme_id,
            current_user_id,
            share_id=share_id,
            revoked_user_id=share.user_id,
            revoked_group_id=share.group_id
        )

        return '', 204

    except Exception as e:
        db.session.rollback()
        current_app.logger.error(f"Error revoking share: {str(e)}")
        return jsonify({"error": str(e)}), 500


@scheme_sharing_bp.route('/<scheme_id>/shares', methods=['GET'])
def list_shares(scheme_id):
    """
    List all shares for a marking scheme (T120).

    GET /api/schemes/{id}/shares

    Response:
        200: List of shares
        403: User is not owner
        404: Scheme not found
    """
    try:
        current_user_id = get_current_user_id()
        if not current_user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Check if scheme exists
        scheme = GradingScheme.query.filter_by(id=scheme_id).first()
        if not scheme:
            scheme = MarkingScheme.query.filter_by(id=scheme_id).first()
            if not scheme:
                return jsonify({"error": "Scheme not found"}), 404

        # Verify user is owner
        if hasattr(scheme, 'created_by') and scheme.created_by != current_user_id:
            return jsonify({"error": "Only scheme owner can list shares"}), 403

        # Get all shares for this scheme
        shares = SchemeShare.query.filter_by(scheme_id=scheme_id).all()

        return jsonify({
            "shares": [share.to_dict() for share in shares]
        }), 200

    except Exception as e:
        current_app.logger.error(f"Error listing shares: {str(e)}")
        return jsonify({"error": str(e)}), 500


@scheme_sharing_bp.route('/shared-with-me', methods=['GET'])
def list_shared_schemes():
    """
    List all schemes shared with current user (T121).

    GET /api/schemes/shared-with-me?permission_filter=VIEW_ONLY

    Query parameters:
        permission_filter: Optional filter by permission level

    Response:
        200: List of shared schemes
    """
    try:
        current_user_id = get_current_user_id()
        if not current_user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Get permission filter
        permission_filter = request.args.get('permission_filter')

        # Get accessible schemes
        accessible = PermissionChecker.get_user_accessible_schemes(current_user_id)

        schemes_data = []
        for scheme, permission in accessible:
            # Apply filter if provided
            if permission_filter and permission != permission_filter:
                continue

            # Get share info
            share = SchemeShare.query.filter_by(
                scheme_id=scheme.id,
                user_id=current_user_id
            ).filter(
                SchemeShare.revoked_at.is_(None)
            ).first()

            # Get owner info
            owner_name = "Unknown"
            if hasattr(scheme, 'created_by') and scheme.created_by:
                owner = User.query.filter_by(id=scheme.created_by).first()
                if owner:
                    owner_name = owner.display_name or owner.email

            # Get shared_by info
            shared_by_email = "Unknown"
            if share and share.shared_by_id:
                shared_by = User.query.filter_by(id=share.shared_by_id).first()
                if shared_by:
                    shared_by_email = shared_by.email

            # Count criteria
            criteria_count = 0
            if hasattr(scheme, 'questions'):
                for question in scheme.questions:
                    if hasattr(question, 'criteria'):
                        criteria_count += len(question.criteria)

            schemes_data.append({
                "id": scheme.id,
                "name": scheme.name,
                "owner": owner_name,
                "permission": permission,
                "shared_at": share.shared_at.isoformat() if share and share.shared_at else None,
                "shared_by": shared_by_email,
                "criteria_count": criteria_count
            })

        return jsonify({"schemes": schemes_data}), 200

    except Exception as e:
        current_app.logger.error(f"Error listing shared schemes: {str(e)}")
        return jsonify({"error": str(e)}), 500
