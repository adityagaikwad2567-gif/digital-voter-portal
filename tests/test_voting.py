"""Tests for the voting flow: cast vote, duplicate prevention, results."""
from tests.conftest import login_voter, login_voter2, login_admin
from app.services.db_operations import cast_vote, has_voted, get_election_results


class TestVotingHub:
    """Tests for the voting index and active elections pages."""

    def test_voting_index_requires_login(self, client):
        """GET /voting/ without login should redirect to login."""
        r = client.get('/voting/', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_voting_index_renders_for_voter(self, client):
        """GET /voting/ should render for logged-in voter."""
        login_voter(client)
        r = client.get('/voting/')
        assert r.status_code == 200
        assert b'Online Voting' in r.data

    def test_active_elections_page_renders(self, client):
        """GET /voting/active should list active elections."""
        login_voter(client)
        r = client.get('/voting/active')
        assert r.status_code == 200
        assert b'Active Elections' in r.data
        assert b'Test Election Active' in r.data


class TestCastVote:
    """Tests for the cast-vote flow."""

    def test_cast_vote_page_renders_for_active_election(self, client):
        """GET /voting/cast/1 should show candidates for active election."""
        login_voter(client)
        r = client.get('/voting/cast/1')
        assert r.status_code == 200
        assert b'Candidate Alpha' in r.data
        assert b'Candidate Beta' in r.data

    def test_cast_vote_redirects_for_inactive_election(self, client):
        """GET /voting/cast/2 (completed) should redirect."""
        login_voter(client)
        r = client.get('/voting/cast/2', follow_redirects=False)
        assert r.status_code == 302
        assert '/voting/active' in r.headers['Location']

    def test_cast_vote_redirects_for_nonexistent_election(self, client):
        """GET /voting/cast/999 (doesn't exist) should redirect."""
        login_voter(client)
        r = client.get('/voting/cast/999', follow_redirects=False)
        assert r.status_code == 302

    def test_post_without_candidate_flash_warning(self, client):
        """POST to cast without selecting a candidate should re-render."""
        login_voter(client)
        r = client.post('/voting/cast/1', data={}, follow_redirects=True)
        assert r.status_code == 200
        assert b'select a candidate' in r.data.lower()

    def test_post_with_candidate_redirects_to_confirm(self, client):
        """POST with a candidate_id should redirect to confirmation."""
        login_voter(client)
        r = client.post('/voting/cast/1', data={'candidate_id': '1'}, follow_redirects=False)
        assert r.status_code == 302
        assert '/voting/confirm/1/1' in r.headers['Location']


class TestConfirmVote:
    """Tests for the vote confirmation step."""

    def test_confirm_page_renders(self, client):
        """GET /voting/confirm/1/1 should show confirmation page."""
        login_voter(client)
        r = client.get('/voting/confirm/1/1')
        assert r.status_code == 200
        assert b'Confirm' in r.data
        assert b'Candidate Alpha' in r.data

    def test_confirm_invalid_candidate_redirects(self, client):
        """GET /voting/confirm/1/999 should redirect (bad candidate)."""
        login_voter(client)
        r = client.get('/voting/confirm/1/999', follow_redirects=False)
        assert r.status_code == 302
        assert '/voting/cast/1' in r.headers['Location']

    def test_confirm_incomplete_election_redirects(self, client):
        """GET /voting/confirm/2/3 (completed election) should redirect."""
        login_voter(client)
        r = client.get('/voting/confirm/2/3', follow_redirects=False)
        assert r.status_code == 302
        assert '/voting/active' in r.headers['Location']

    def test_post_confirm_records_vote(self, client):
        """POST to confirm should record the vote and show success."""
        login_voter(client)
        r = client.post('/voting/confirm/1/1', follow_redirects=False)
        assert r.status_code == 200
        assert b'Successfully' in r.data or b'Recorded' in r.data or b'vote' in r.data.lower()
        assert b'VOTE-1-2-' in r.data  # reference code pattern

    def test_duplicate_vote_prevented(self, client):
        """Second vote by same voter in same election should fail."""
        login_voter(client)
        # First vote
        client.post('/voting/confirm/1/1', follow_redirects=False)
        # Second vote attempt
        r = client.get('/voting/cast/1', follow_redirects=False)
        assert r.status_code == 302
        # Should be redirected (already voted)
        # The route checks has_voted and redirects
        follow = client.get('/voting/cast/1', follow_redirects=True)
        assert b'already voted' in follow.data.lower()


class TestVoteProcessing:
    """Tests for the cast_vote function at the service level."""

    def test_cast_vote_success(self, app, app_context):
        """cast_vote should return a vote_id and reference code."""
        vote_id, ref_code = cast_vote(1, 2, 1)  # election=1, voter=2, candidate=1
        assert vote_id is not None
        assert ref_code.startswith('VOTE-1-2-')

    def test_cast_vote_duplicate_rejected(self, app, app_context):
        """cast_vote should reject duplicate votes."""
        cast_vote(1, 2, 1)  # first vote
        vote_id, msg = cast_vote(1, 2, 2)  # duplicate
        assert vote_id is None
        assert 'already voted' in msg.lower()

    def test_cast_vote_inactive_election_rejected(self, app, app_context):
        """cast_vote should reject votes in non-active elections."""
        vote_id, msg = cast_vote(2, 2, 3)  # election 2 is Completed
        assert vote_id is None
        assert 'not currently active' in msg.lower()

    def test_cast_vote_invalid_candidate_rejected(self, app, app_context):
        """cast_vote should reject candidates not in the election."""
        vote_id, msg = cast_vote(1, 2, 999)
        assert vote_id is None
        assert 'invalid candidate' in msg.lower()

    def test_has_voted_before_casting(self, app, app_context):
        """has_voted should be False before any vote."""
        assert has_voted(1, 2) is False

    def test_has_voted_after_casting(self, app, app_context):
        """has_voted should be True after voting."""
        cast_vote(1, 2, 1)
        assert has_voted(1, 2) is True


class TestVotingHistory:
    """Tests for voting history."""

    def test_voting_history_requires_login(self, client):
        """GET /voting/history should redirect if not logged in."""
        r = client.get('/voting/history', follow_redirects=False)
        assert r.status_code == 302
        assert '/auth/login' in r.headers['Location']

    def test_voting_history_empty_for_new_voter(self, client):
        """New voter should have empty voting history."""
        login_voter(client)
        r = client.get('/voting/history')
        assert r.status_code == 200
        assert b'Voting History' in r.data

    def test_voting_history_shows_after_vote(self, client):
        """After voting, history should show the election."""
        login_voter(client)
        # Cast a vote
        client.post('/voting/confirm/1/1', follow_redirects=False)
        # Check history
        r = client.get('/voting/history')
        assert r.status_code == 200
        assert b'Test Election Active' in r.data
        assert b'Recorded' in r.data


class TestElectionResults:
    """Tests for election results."""

    def test_results_list_renders(self, client):
        """GET /elections/results should show completed elections."""
        r = client.get('/elections/results')
        assert r.status_code == 200
        assert b'Results' in r.data

    def test_results_detail_renders(self, client):
        """GET /elections/results/1 should show results for election 1."""
        r = client.get('/elections/results/1')
        assert r.status_code == 200
        assert b'Test Election Active' in r.data

    def test_get_election_results_structure(self, app, app_context):
        """get_election_results should return correct structure."""
        results = get_election_results(1)
        assert results is not None
        assert 'election' in results
        assert 'candidates' in results
        assert 'total_votes' in results
        assert results['total_votes'] == 0  # no votes cast yet
        assert len(results['candidates']) == 2  # Alpha and Beta

    def test_results_update_after_voting(self, app, app_context):
        """Results should reflect votes after casting."""
        cast_vote(1, 2, 1)  # voter 2 votes for candidate 1
        cast_vote(1, 3, 1)  # voter 3 votes for candidate 1
        results = get_election_results(1)
        assert results['total_votes'] == 2
        alpha = [c for c in results['candidates'] if c['name'] == 'Candidate Alpha'][0]
        assert alpha['vote_count'] == 2
        assert alpha['percentage'] == 100.0

    def test_results_percentage_calculation(self, app, app_context):
        """Percentages should add up correctly."""
        cast_vote(1, 2, 1)  # Alpha
        cast_vote(1, 3, 2)  # Beta
        results = get_election_results(1)
        total_pct = sum(c['percentage'] for c in results['candidates'])
        assert abs(total_pct - 100.0) < 0.1


class TestMultiVoterIsolation:
    """Tests ensuring different voters are independent."""

    def test_two_voters_can_vote_independently(self, app, app_context):
        """Two different voters should both be able to vote."""
        vid1, _ = cast_vote(1, 2, 1)
        vid2, _ = cast_vote(1, 3, 2)
        assert vid1 is not None
        assert vid2 is not None
        assert vid1 != vid2

    def test_voter2_duplicate_rejected(self, app, app_context):
        """Voter2's duplicate vote should be rejected independently."""
        cast_vote(1, 2, 1)
        cast_vote(1, 3, 2)
        vote_id, msg = cast_vote(1, 3, 1)
        assert vote_id is None
        assert 'already voted' in msg.lower()
