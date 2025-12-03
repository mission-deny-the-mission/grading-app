"""
Tests for schemes_ui routes - covering all scheme UI endpoints.
"""

import pytest
from unittest.mock import patch


class TestSchemesUIRoutes:
    """Test cases for schemes UI routes."""

    def test_list_schemes_success(self, client, app):
        """Test the schemes list page loads successfully."""
        with app.app_context():
            from models import db, GradingScheme

            # Create some test schemes
            for i in range(3):
                scheme = GradingScheme(
                    name=f"Test Scheme {i}",
                    total_possible_points=100.0
                )
                db.session.add(scheme)
            db.session.commit()

        response = client.get("/schemes/")
        assert response.status_code == 200

    def test_list_schemes_with_pagination(self, client, app):
        """Test schemes list with pagination parameters."""
        with app.app_context():
            from models import db, GradingScheme

            # Create many schemes
            for i in range(25):
                scheme = GradingScheme(
                    name=f"Scheme {i}",
                    total_possible_points=100.0
                )
                db.session.add(scheme)
            db.session.commit()

        response = client.get("/schemes/?page=2&per_page=10")
        assert response.status_code == 200

    def test_list_schemes_with_search(self, client, app):
        """Test schemes list with search filter."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Unique Searchable Name",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()

        response = client.get("/schemes/?search=Unique")
        assert response.status_code == 200

    def test_list_schemes_sort_by_name(self, client, app):
        """Test schemes list sorted by name."""
        response = client.get("/schemes/?sort=name&order=asc")
        assert response.status_code == 200

    def test_list_schemes_sort_by_total_points(self, client, app):
        """Test schemes list sorted by total points."""
        response = client.get("/schemes/?sort=total_points&order=desc")
        assert response.status_code == 200

    def test_list_schemes_sort_default(self, client, app):
        """Test schemes list with default sorting (created_at)."""
        response = client.get("/schemes/?sort=created_at&order=desc")
        assert response.status_code == 200

    def test_list_schemes_max_per_page(self, client, app):
        """Test that per_page is capped at 100."""
        response = client.get("/schemes/?per_page=200")
        assert response.status_code == 200

    def test_list_schemes_exception_handling(self, client, app):
        """Test exception handling in list_schemes route."""
        with patch("routes.schemes_ui.GradingScheme") as mock_model:
            mock_model.query.filter_by.side_effect = Exception("Database error")
            response = client.get("/schemes/")
            # Should still return 200 with empty schemes
            assert response.status_code == 200

    def test_view_scheme_success(self, client, app):
        """Test viewing a specific scheme."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="View Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}")
        assert response.status_code == 200

    def test_view_scheme_not_found(self, client, app):
        """Test viewing a non-existent scheme."""
        response = client.get("/schemes/nonexistent-id")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_view_deleted_scheme(self, client, app):
        """Test viewing a soft-deleted scheme."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Deleted Scheme",
                total_possible_points=100.0,
                is_deleted=True
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_view_scheme_exception_handling(self, client, app):
        """Test exception handling in view_scheme route."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Exception Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        with patch("routes.schemes_ui.render_template") as mock_render:
            mock_render.side_effect = Exception("Template error")
            response = client.get(f"/schemes/{scheme_id}")
            # Should redirect due to exception
            assert response.status_code == 302

    def test_create_scheme_form(self, client, app):
        """Test the create scheme form page."""
        response = client.get("/schemes/create")
        assert response.status_code == 200

    def test_edit_scheme_success(self, client, app):
        """Test the edit scheme form page."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Edit Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}/edit")
        assert response.status_code == 200

    def test_edit_scheme_not_found(self, client, app):
        """Test editing a non-existent scheme."""
        response = client.get("/schemes/nonexistent-id/edit")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_edit_deleted_scheme(self, client, app):
        """Test editing a soft-deleted scheme."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Deleted Scheme",
                total_possible_points=100.0,
                is_deleted=True
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}/edit")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_edit_scheme_exception_handling(self, client, app):
        """Test exception handling in edit_scheme route."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Exception Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        with patch("routes.schemes_ui.render_template") as mock_render:
            mock_render.side_effect = Exception("Template error")
            response = client.get(f"/schemes/{scheme_id}/edit")
            # Should redirect due to exception
            assert response.status_code == 302

    def test_view_statistics_success(self, client, app):
        """Test the statistics page for a scheme."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Stats Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}/statistics")
        assert response.status_code == 200

    def test_view_statistics_not_found(self, client, app):
        """Test statistics page for non-existent scheme."""
        response = client.get("/schemes/nonexistent-id/statistics")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_view_statistics_deleted_scheme(self, client, app):
        """Test statistics page for soft-deleted scheme."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Deleted Scheme",
                total_possible_points=100.0,
                is_deleted=True
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}/statistics")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_view_statistics_exception_handling(self, client, app):
        """Test exception handling in view_statistics route."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Exception Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        with patch("routes.schemes_ui.render_template") as mock_render:
            mock_render.side_effect = Exception("Template error")
            response = client.get(f"/schemes/{scheme_id}/statistics")
            # Should redirect due to exception
            assert response.status_code == 302

    def test_clone_scheme_form_success(self, client, app):
        """Test the clone scheme form page."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Clone Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}/clone")
        assert response.status_code == 200

    def test_clone_scheme_form_not_found(self, client, app):
        """Test clone form for non-existent scheme."""
        response = client.get("/schemes/nonexistent-id/clone")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_clone_scheme_form_deleted(self, client, app):
        """Test clone form for soft-deleted scheme."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Deleted Scheme",
                total_possible_points=100.0,
                is_deleted=True
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        response = client.get(f"/schemes/{scheme_id}/clone")
        # Should redirect with flash message
        assert response.status_code == 302

    def test_clone_scheme_exception_handling(self, client, app):
        """Test exception handling in clone_scheme_form route."""
        with app.app_context():
            from models import db, GradingScheme

            scheme = GradingScheme(
                name="Exception Test Scheme",
                total_possible_points=100.0
            )
            db.session.add(scheme)
            db.session.commit()
            scheme_id = scheme.id

        with patch("routes.schemes_ui.render_template") as mock_render:
            mock_render.side_effect = Exception("Template error")
            response = client.get(f"/schemes/{scheme_id}/clone")
            # Should redirect due to exception
            assert response.status_code == 302
