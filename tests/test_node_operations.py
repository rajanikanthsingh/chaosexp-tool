"""Tests for node drain and recovery operations."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

from chaosmonkey.cli import app
from chaosmonkey.core.nomad import NomadClient


class TestNomadClientNodeOperations:
    """Test NomadClient node drain and recovery methods."""

    def test_list_nodes_stub_fallback(self):
        """Test node listing with stub fallback."""
        client = NomadClient("http://localhost:4646")
        client._client = None  # Force stub mode
        
        nodes = client.list_nodes()
        
        assert len(nodes) == 2
        assert nodes[0]["Name"] == "client-01"
        assert nodes[1]["Name"] == "client-02"
        assert all("ID" in node for node in nodes)

    @patch('nomad.Nomad')
    def test_list_nodes_real_client(self, mock_nomad_class):
        """Test node listing with real Nomad client."""
        mock_client = Mock()
        mock_nomad_class.return_value = mock_client
        mock_client.nodes.get_nodes.return_value = [
            {"ID": "node-123", "Name": "real-worker", "Status": "ready"},
            {"ID": "node-456", "Name": "real-worker-2", "Status": "ready"}
        ]
        mock_client.node.get_node.return_value = {"Drain": False, "SchedulingEligibility": "eligible"}
        
        client = NomadClient("http://localhost:4646")
        nodes = client.list_nodes()
        
        assert len(nodes) == 2
        assert nodes[0]["Name"] == "real-worker"
        mock_client.nodes.get_nodes.assert_called_once()

    @patch('requests.post')
    def test_drain_node_success(self, mock_post):
        """Test successful node drain."""
        mock_post.return_value.status_code = 200
        
        client = NomadClient("http://localhost:4646", token="test-token")
        result = client.drain_node("node-123")
        
        assert result is True
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert "node-123/drain" in call_args[0][0]  # URL is first positional arg
        assert call_args[1]["json"]["DrainSpec"]["Deadline"] == 300000000000  # 5 minutes in nanoseconds

    @patch('requests.post')
    def test_drain_node_failure(self, mock_post):
        """Test failed node drain."""
        mock_post.return_value.status_code = 500
        
        client = NomadClient("http://localhost:4646")
        result = client.drain_node("node-123")
        
        assert result is False

    @patch('requests.post')
    def test_recover_node_success(self, mock_post):
        """Test successful node recovery."""
        mock_post.return_value.status_code = 200
        
        client = NomadClient("http://localhost:4646")
        result = client.recover_node("node-123")
        
        assert result is True
        assert mock_post.call_count == 2  # drain disable + eligibility enable

    def test_recover_node_stub_mode(self):
        """Test node recovery in stub mode."""
        client = NomadClient("http://localhost:4646")
        client._client = None  # Force stub mode
        
        result = client.recover_node("node-123")
        
        assert result is True  # Always succeeds in stub mode


class TestDrainNodesCommand:
    """Test drain-nodes CLI command."""

    def setup_method(self):
        self.runner = CliRunner()

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_drain_nodes_dry_run(self, mock_client_class):
        """Test drain-nodes command with dry-run."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = [
            {"ID": "node-123", "Name": "worker-01", "Status": "ready", "Drain": False, "SchedulingEligibility": "eligible"}
        ]
        
        result = self.runner.invoke(app, [
            "drain-nodes", 
            "--node-id", "node-123",
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.stdout
        assert "worker-01" in result.stdout
        mock_client.drain_node.assert_not_called()

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_drain_nodes_with_confirmation_yes(self, mock_client_class):
        """Test drain-nodes command with --yes flag."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = [
            {"ID": "node-123", "Name": "worker-01", "Status": "ready", "Drain": False, "SchedulingEligibility": "eligible"}
        ]
        mock_client.drain_node.return_value = True
        
        result = self.runner.invoke(app, [
            "drain-nodes",
            "--node-id", "node-123", 
            "--yes"
        ])
        
        assert result.exit_code == 0
        assert "Successfully drained" in result.stdout
        mock_client.drain_node.assert_called_once_with("node-123", 300)

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_drain_nodes_no_nodes_found(self, mock_client_class):
        """Test drain-nodes when no eligible nodes found.""" 
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = []
        
        result = self.runner.invoke(app, [
            "drain-nodes",
            "--node-id", "nonexistent"
        ])
        
        assert result.exit_code == 0  # Command completes normally but shows not found message
        assert "not found" in result.stdout

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_drain_nodes_failure(self, mock_client_class):
        """Test drain-nodes when drain operation fails."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = [
            {"ID": "node-123", "Name": "worker-01", "Status": "ready", "Drain": False, "SchedulingEligibility": "eligible"}
        ]
        mock_client.drain_node.return_value = False
        
        result = self.runner.invoke(app, [
            "drain-nodes",
            "--node-id", "node-123",
            "--yes"
        ])
        
        assert result.exit_code == 1
        assert "Failed to drain" in result.stdout


class TestRecoverNodesCommand:
    """Test recover-nodes CLI command."""

    def setup_method(self):
        self.runner = CliRunner()

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_recover_nodes_dry_run(self, mock_client_class):
        """Test recover-nodes command with dry-run."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = [
            {
                "ID": "node-123",
                "Name": "worker-01", 
                "Drain": True,
                "SchedulingEligibility": "ineligible",
                "Status": "ready"
            }
        ]
        
        result = self.runner.invoke(app, [
            "recover-nodes",
            "--dry-run"
        ])
        
        assert result.exit_code == 0
        assert "DRY RUN MODE" in result.stdout
        assert "worker-01" in result.stdout
        mock_client.recover_node.assert_not_called()

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_recover_nodes_no_drained_nodes(self, mock_client_class):
        """Test recover-nodes when no drained nodes found."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = [
            {"ID": "node-123", "Name": "worker-01", "Status": "ready", "Drain": False, "SchedulingEligibility": "eligible"}
        ]
        
        result = self.runner.invoke(app, [
            "recover-nodes"
        ])
        
        assert result.exit_code == 0
        assert "No drained nodes found" in result.stdout

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_recover_nodes_success_with_yes(self, mock_client_class):
        """Test recover-nodes with --yes flag."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = [
            {
                "ID": "node-123",
                "Name": "worker-01",
                "Drain": True, 
                "SchedulingEligibility": "ineligible",
                "Status": "ready"
            }
        ]
        mock_client.recover_node.return_value = True
        
        result = self.runner.invoke(app, [
            "recover-nodes",
            "--yes"
        ])
        
        assert result.exit_code == 0
        assert "Successfully recovered" in result.stdout
        mock_client.recover_node.assert_called_once_with("node-123")

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_recover_nodes_partial_failure(self, mock_client_class):
        """Test recover-nodes with mixed success/failure."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        mock_client.list_nodes.return_value = [
            {"ID": "node-123", "Name": "worker-01", "Drain": True, "SchedulingEligibility": "ineligible", "Status": "ready"},
            {"ID": "node-456", "Name": "worker-02", "Drain": True, "SchedulingEligibility": "ineligible", "Status": "ready"}
        ]
        
        # First recovery succeeds, second fails
        mock_client.recover_node.side_effect = [True, False]
        
        result = self.runner.invoke(app, [
            "recover-nodes",
            "--yes"
        ])
        
        assert result.exit_code == 0
        assert "Successfully recovered 1" in result.stdout
        assert "Failed to recover 1" in result.stdout


@pytest.mark.integration
class TestNodeOperationsIntegration:
    """Integration tests for node operations workflow."""

    @patch('chaosmonkey.core.nomad.NomadClient')
    def test_full_drain_and_recover_workflow(self, mock_client_class):
        """Test complete drain → recover workflow."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        # Setup: healthy nodes available
        mock_client.list_nodes.return_value = [
            {"ID": "node-123", "Name": "worker-01", "Status": "ready", "Drain": False, "SchedulingEligibility": "eligible"}
        ]
        mock_client.drain_node.return_value = True
        mock_client.recover_node.return_value = True
        
        runner = CliRunner()
        
        # Step 1: Drain the node
        drain_result = runner.invoke(app, [
            "drain-nodes",
            "--node-id", "node-123",
            "--yes"
        ])
        assert drain_result.exit_code == 0
        assert "Successfully drained" in drain_result.stdout
        
        # Update mock for recovery: node is now drained
        mock_client.list_nodes.return_value = [
            {"ID": "node-123", "Name": "worker-01", "Status": "ready", "Drain": True, "SchedulingEligibility": "ineligible"}
        ]
        
        # Step 2: Recover the node  
        recover_result = runner.invoke(app, [
            "recover-nodes",
            "--node-id", "node-123",
            "--yes"
        ])
        assert recover_result.exit_code == 0
        assert "Successfully recovered" in recover_result.stdout
        
        # Verify both operations were called
        mock_client.drain_node.assert_called_once_with("node-123", 300)
        mock_client.recover_node.assert_called_once_with("node-123")