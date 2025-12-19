# tests/test_trigger.py
import unittest
from unittest.mock import patch, MagicMock
from src.pre_gambling_flow.nodes import trigger

class TestTrigger(unittest.TestCase):

    @patch('src.pre_gambling_flow.nodes.trigger.BlockingScheduler')
    @patch('src.pre_gambling_flow.nodes.trigger.load_config')
    def test_main_schedule_job(self, mock_load_config, mock_scheduler):
        """
        Tests that the main function correctly schedules the job
        with the time from the config.
        """
        mock_load_config.return_value = {
            "scheduler": {
                "pre_gambling_trigger_time": "15:30"
            }
        }
        mock_scheduler_instance = MagicMock()
        mock_scheduler.return_value = mock_scheduler_instance

        trigger.main()

        mock_scheduler_instance.add_job.assert_called_once_with(
            trigger.run_pre_gambling_flow,
            "cron",
            hour=15,
            minute=30,
            misfire_grace_time=600,
            coalesce=True,
        )
        mock_scheduler_instance.start.assert_called_once()

    @patch('src.pre_gambling_flow.main.PreGamblingFlow')
    def test_run_pre_gambling_flow_success(self, mock_flow):
        """
        Tests that the run_pre_gambling_flow function
        instantiates and runs the flow.
        """
        mock_flow_instance = MagicMock()
        mock_flow.return_value = mock_flow_instance

        trigger.run_pre_gambling_flow()

        mock_flow.assert_called_once()
        mock_flow_instance.run.assert_called_once()

if __name__ == '__main__':
    unittest.main()
