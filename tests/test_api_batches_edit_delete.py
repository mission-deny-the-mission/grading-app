"""
Batch update and delete endpoint tests to increase routes.api coverage.
"""

import json


class TestBatchEditDelete:
    def test_update_and_delete_batch(self, client, app):
        with app.app_context():
            from models import JobBatch, db
            batch = JobBatch(batch_name='ToUpdate', description='d', priority=3)
            db.session.add(batch)
            db.session.commit()
            bid = batch.id

        # Update
        resp = client.put(f'/api/batches/{bid}', json={'batch_name': 'UpdatedName', 'priority': 7})
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True and data['batch']['batch_name'] == 'UpdatedName'
        assert data['batch']['priority'] == 7

        # Delete
        resp = client.delete(f'/api/batches/{bid}')
        assert resp.status_code == 200
        data = json.loads(resp.data)
        assert data['success'] is True


