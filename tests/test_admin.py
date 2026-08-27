"""Tests for admin workflows: dashboard, voter CRUD, election CRUD, grievances."""
from tests.conftest import login_admin, login_voter
from app.services.db_operations import (
    get_dashboard_stats, get_all_voters,
    create_election, get_election, update_election_status,
    create_candidate, get_all_candidates, get_candidates_for_election,
    get_all_polling_stations, create_polling_station,
    get_all_grievances, update_grievance_status,
    get_audit_logs, get_all_applications,
    update_voter_status, get_voter_profile_with_user,
)


class TestAdminDashboard:
    """Tests for the admin dashboard."""

    def test_dashboard_requires_admin(self, client):
        """GET /admin/ without login should redirect to login."""
        r = client.get('/admin/', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_dashboard_requires_admin_role(self, client):
        """Voter cannot access admin dashboard."""
        login_voter(client)
        r = client.get('/admin/', follow_redirects=False)
        assert r.status_code == 302
        # Should redirect to home (access denied)
        assert '/admin/' not in r.headers['Location']

    def test_dashboard_renders_for_admin(self, client):
        """GET /admin/ should render for admin."""
        login_admin(client)
        r = client.get('/admin/')
        assert r.status_code == 200
        assert b'Admin Dashboard' in r.data

    def test_dashboard_shows_stats(self, client):
        """Dashboard should show voter/election statistics."""
        login_admin(client)
        r = client.get('/admin/')
        assert r.status_code == 200
        assert b'Registered Voters' in r.data
        assert b'Active Elections' in r.data

    def test_dashboard_stats_structure(self, app, app_context):
        """get_dashboard_stats should return expected keys."""
        stats = get_dashboard_stats()
        assert 'total_voters' in stats
        assert 'active_elections' in stats
        assert stats['total_voters'] == 2  # 2 VOTER-role users in seed data


class TestVoterManagement:
    """Tests for admin voter management."""

    def test_voters_page_renders(self, client):
        """GET /admin/voters should list voters."""
        login_admin(client)
        r = client.get('/admin/voters')
        assert r.status_code == 200
        assert b'Voter Management' in r.data

    def test_voter_list_contains_seeded_data(self, client):
        """Voters list should contain seeded demo voters."""
        login_admin(client)
        r = client.get('/admin/voters')
        assert b'Test Voter' in r.data
        assert b'Second Voter' in r.data

    def test_voter_search(self, client):
        """Search for a specific voter should filter results."""
        login_admin(client)
        r = client.get('/admin/voters?search=Test+Voter')
        assert r.status_code == 200
        assert b'Test Voter' in r.data

    def test_view_voter_page(self, client):
        """GET /admin/voter/2 should show voter details."""
        login_admin(client)
        r = client.get('/admin/voter/2')
        assert r.status_code == 200
        assert b'Test Voter' in r.data

    def test_edit_voter_page(self, client):
        """GET /admin/voter/2/edit should show edit form."""
        login_admin(client)
        r = client.get('/admin/voter/2/edit')
        assert r.status_code == 200
        assert b'Edit Voter' in r.data

    def test_edit_voter_updates_data(self, client, app, app_context):
        """POST to edit voter should update the database."""
        login_admin(client)
        r = client.post('/admin/voter/2/edit', data={
            'name': 'Updated Voter Name',
            'email': 'voter@demo.local',
            'mobile': '9100000001',
            'status': 'active',
            'dob': '2004-05-15',
            'gender': 'Male',
            'address': '123 Updated Street',
            'state': 'Maharashtra',
            'district': 'Akola',
            'constituency': 'Test Constituency',
            'pincode': '444001',
            'role': 'VOTER',
        }, follow_redirects=True)
        assert r.status_code == 200

        with app.app_context():
            profile = get_voter_profile_with_user(2)
            assert profile['name'] == 'Updated Voter Name'

    def test_add_voter_page(self, client):
        """GET /admin/voter/add should show the add form."""
        login_admin(client)
        r = client.get('/admin/voter/add')
        assert r.status_code == 200
        assert b'Add Voter' in r.data or b'add' in r.data.lower()

    def test_add_voter_creates_user(self, client, app, app_context):
        """POST to add voter should create a new user."""
        login_admin(client)
        r = client.post('/admin/voter/add', data={
            'name': 'Brand New Voter',
            'email': 'brandnew@demo.local',
            'mobile': '9999988888',
            'password': 'TestPass@123',
            'dob': '2003-01-15',
            'gender': 'Male',
            'address': '789 New Road',
            'state': 'Maharashtra',
            'district': 'Mumbai',
            'constituency': 'Mumbai Central',
            'pincode': '400001',
            'role': 'VOTER',
        }, follow_redirects=False)
        assert r.status_code == 302  # Redirects to voters list

        with app.app_context():
            voters, total = get_all_voters(per_page=100)
            emails = [v['email'] for v in voters]
            assert 'brandnew@demo.local' in emails

    def test_deactivate_voter(self, client, app, app_context):
        """POST to toggle-status should change voter status."""
        login_admin(client)
        r = client.post('/admin/voter/3/toggle-status', follow_redirects=True)
        assert r.status_code == 200

        with app.app_context():
            profile = get_voter_profile_with_user(3)
            assert profile['status'] == 'inactive'


class TestElectionManagement:
    """Tests for admin election management."""

    def test_elections_page_renders(self, client):
        """GET /admin/elections should list elections."""
        login_admin(client)
        r = client.get('/admin/elections')
        assert r.status_code == 200
        assert b'Election Management' in r.data

    def test_create_election_page(self, client):
        """GET /admin/election/create should render form."""
        login_admin(client)
        r = client.get('/admin/election/create')
        assert r.status_code == 200
        assert b'Create Election' in r.data or b'Election' in r.data

    def test_create_election(self, client, app, app_context):
        """POST to create election should add to database."""
        login_admin(client)
        r = client.post('/admin/election/create', data={
            'name': 'Brand New Election',
            'description': 'A test election',
            'election_type': 'Student Council',
            'constituency': 'All',
            'start_time': '2026-09-01T09:00',
            'end_time': '2026-09-07T17:00',
        }, follow_redirects=False)
        assert r.status_code == 302

        with app.app_context():
            election = get_election(3)  # should be id 3
            assert election is not None
            assert election['name'] == 'Brand New Election'
            assert election['status'] == 'Upcoming'

    def test_edit_election_page(self, client):
        """GET /admin/election/1/edit should render."""
        login_admin(client)
        r = client.get('/admin/election/1/edit')
        assert r.status_code == 200
        assert b'Edit Election' in r.data

    def test_activate_election(self, client, app, app_context):
        """POST to activate should change election status to Active."""
        # Create an upcoming election first
        with app.app_context():
            create_election(
                'To Activate', 'desc', 'Test', 'All',
                '2026-09-01 09:00:00', '2026-09-07 17:00:00'
            )

        login_admin(client)
        r = client.post('/admin/election/3/activate', follow_redirects=True)
        assert r.status_code == 200

        with app.app_context():
            election = get_election(3)
            assert election['status'] == 'Active'

    def test_close_election(self, client, app, app_context):
        """POST to close should change election status to Completed."""
        login_admin(client)
        r = client.post('/admin/election/1/close', follow_redirects=True)
        assert r.status_code == 200

        with app.app_context():
            election = get_election(1)
            assert election['status'] == 'Completed'

    def test_elections_list_shows_all(self, client):
        """Elections page should show both active and completed."""
        login_admin(client)
        r = client.get('/admin/elections')
        assert b'Test Election Active' in r.data
        assert b'Test Election Completed' in r.data


class TestCandidateManagement:
    """Tests for admin candidate management."""

    def test_manage_candidates_page(self, client):
        """GET /admin/election/1/candidates should list candidates."""
        login_admin(client)
        r = client.get('/admin/election/1/candidates')
        assert r.status_code == 200
        assert b'Candidate Alpha' in r.data
        assert b'Candidate Beta' in r.data

    def test_add_candidate(self, client, app, app_context):
        """POST to add candidate should create candidate."""
        login_admin(client)
        r = client.post('/admin/election/1/add-candidate', data={
            'name': 'Candidate Charlie',
            'party_name': 'Party C',
            'symbol': 'Diamond',
            'description': 'Charlie candidate description',
        }, follow_redirects=True)
        assert r.status_code == 200

        with app.app_context():
            candidates = get_candidates_for_election(1)
            names = [c['name'] for c in candidates]
            assert 'Candidate Charlie' in names

    def test_candidate_service_create(self, app, app_context):
        """create_candidate should return the new candidate ID."""
        candidate_id = create_candidate(
            1, 'Candidate Delta', 'Party D', 'Heart', 'Delta description'
        )
        assert candidate_id is not None

        candidates = get_candidates_for_election(1)
        names = [c['name'] for c in candidates]
        assert 'Candidate Delta' in names

    def test_all_candidates(self, app, app_context):
        """get_all_candidates should return candidates across elections."""
        all_cands, total = get_all_candidates()
        assert len(all_cands) >= 3  # 2 for election 1 + 1 for election 2


class TestPollingStationManagement:
    """Tests for admin polling station management."""

    def test_polling_stations_page(self, client):
        """GET /admin/polling-stations should list stations."""
        login_admin(client)
        r = client.get('/admin/polling-stations')
        assert r.status_code == 200
        assert b'Polling Station' in r.data

    def test_create_polling_station(self, app, app_context):
        """create_polling_station should add a new station."""
        station_id = create_polling_station(
            'New Station', 'New Address', 'Maharashtra', 'Pune',
            'Pune Central', '02', 400, 'Ramp', 'Toilet, Water'
        )
        assert station_id is not None

        stations, total = get_all_polling_stations(per_page=100)
        names = [s['name'] for s in stations]
        assert 'New Station' in names


class TestGrievanceManagement:
    """Tests for grievance workflows."""

    def test_voter_grievances_page(self, client):
        """GET /grievances/ should render for logged-in voter."""
        login_voter(client)
        r = client.get('/grievances/')
        assert r.status_code == 200
        assert b'Grievance' in r.data

    def test_grievance_submit_page(self, client):
        """GET /grievances/submit should render form."""
        login_voter(client)
        r = client.get('/grievances/submit')
        assert r.status_code == 200
        assert b'Submit' in r.data

    def test_admin_grievances_page(self, client):
        """GET /admin/grievances should list grievances."""
        login_admin(client)
        r = client.get('/admin/grievances')
        assert r.status_code == 200
        assert b'Grievance Management' in r.data

    def test_admin_grievances_contain_seeded(self, client):
        """Admin grievances page should show the seeded grievance."""
        login_admin(client)
        r = client.get('/admin/grievances')
        assert b'GRV-2026-TEST01' in r.data

    def test_update_grievance_status(self, app, app_context):
        """update_grievance_status should change the status."""
        from app.services.db_operations import get_grievance_by_ref
        grievance = get_grievance_by_ref('GRV-2026-TEST01')
        assert grievance is not None
        assert grievance['status'] == 'Submitted'

        update_grievance_status(grievance['id'], 'In Progress')
        updated = get_grievance_by_ref('GRV-2026-TEST01')
        assert updated['status'] == 'In Progress'


class TestAuditLogs:
    """Tests for audit log viewing."""

    def test_audit_logs_page(self, client):
        """GET /admin/audit-logs should render."""
        login_admin(client)
        r = client.get('/admin/audit-logs')
        assert r.status_code == 200
        assert b'Audit Logs' in r.data

    def test_audit_logs_service(self, app, app_context):
        """get_audit_logs should return paginated results."""
        logs, total = get_audit_logs(per_page=10)
        # Should have some logs (at least from login actions)
        assert isinstance(logs, list)
        assert isinstance(total, int)


class TestReports:
    """Tests for admin reports page."""

    def test_reports_page(self, client):
        """GET /admin/reports should render."""
        login_admin(client)
        r = client.get('/admin/reports')
        assert r.status_code == 200
        assert b'Report' in r.data


class TestNotifications:
    """Tests for notification center."""

    def test_notifications_page(self, client):
        """GET /admin/notifications should render."""
        login_admin(client)
        r = client.get('/admin/notifications')
        assert r.status_code == 200
        assert b'Notification' in r.data


class TestSettings:
    """Tests for settings page."""

    def test_settings_page(self, client):
        """GET /admin/settings should render."""
        login_admin(client)
        r = client.get('/admin/settings')
        assert r.status_code == 200
        assert b'Setting' in r.data
