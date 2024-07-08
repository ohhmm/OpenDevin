import datetime
import logging
import os
import shutil
import subprocess

import pytest

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CASES_DIR = os.path.join(SCRIPT_DIR, 'cases')
AGENTHUB_DIR = os.path.join(SCRIPT_DIR, '../../', 'agenthub')


def agents():
    """Retrieves a list of available agents.

    Returns:
        A list of agent names.
    """
    agents = []
    for agent in os.listdir(AGENTHUB_DIR):
        if os.path.isdir(os.path.join(AGENTHUB_DIR, agent)) and agent.endswith(
            '_agent'
        ):
            agents.append(agent)
    return agents


@pytest.fixture(scope='session')
def test_cases_dir():
    """Fixture that provides the directory path for test cases.

    Returns:
        The directory path for test cases.
    """
    return CASES_DIR


@pytest.fixture
def task_file(test_cases_dir, request):
    """Fixture that provides the path to the task file for a test case.

    Args:
        test_cases_dir: The directory path for test cases.
        request: The pytest request object.

    Returns:
        The path to the task file for the test case.
    """
    test_case_dir = os.path.dirname(request.module.__file__)
    task_file_path = os.path.join(test_case_dir, 'task.txt')
    return task_file_path


@pytest.fixture
def workspace_dir(test_cases_dir, request):
    """Fixture that provides the workspace directory for a test case.

    Args:
        test_cases_dir: The directory path for test cases.
        request: The pytest request object.

    Returns:
        The workspace directory for the test case.
    """
    test_case_dir = os.path.dirname(request.module.__file__)
    workspace_dir = os.path.join(test_case_dir, 'workspace')
    return workspace_dir


@pytest.fixture
def model(request):
    """Fixture that provides the model name.

    Args:
        request: The pytest request object.

    Returns:
        The model name, defaulting to "gpt-3.5-turbo".
    """
    return request.config.getoption('model', default='gpt-3.5-turbo')


@pytest.fixture
def run_test_case(test_cases_dir, workspace_dir, request):
    """Fixture that provides a function to run a test case.

    Args:
        test_cases_dir: The directory path for test cases.
        workspace_dir: The workspace directory for the test case.
        request: The pytest request object.

    Returns:
        A function that runs a test case for a given agent and case.
    """

    def _run_test_case(agent, case):
        """Runs a test case for a given agent.

        Args:
            agent: The name of the agent to run the test case for.
            case: The name of the test case to run.

        Returns:
            The path to the workspace directory for the agent and test case.

        Raises:
            AssertionError: If the test case execution fails (non-zero return code).

        Steps:
        """
        case_dir = os.path.join(test_cases_dir, case)
        task = open(os.path.join(case_dir, 'task.txt'), 'r').read().strip()
        outputs_dir = os.path.join(case_dir, 'outputs')
        agent_dir = os.path.join(outputs_dir, agent)

        if not os.path.exists(agent_dir):
            os.makedirs(agent_dir)

        shutil.rmtree(os.path.join(agent_dir, 'workspace'), ignore_errors=True)
        if os.path.isdir(os.path.join(case_dir, 'start')):
            os.copytree(
                os.path.join(case_dir, 'start'), os.path.join(agent_dir, 'workspace')
            )
        else:
            os.makedirs(os.path.join(agent_dir, 'workspace'))

        # Create the hello_world.sh script if it does not exist
        hello_world_script_path = os.path.join(agent_dir, 'workspace', 'hello_world.sh')
        if not os.path.isfile(hello_world_script_path):
            with open(hello_world_script_path, 'w') as f:
                f.write('#!/bin/bash\n')
                f.write('echo "Hello, World!"\n')
            os.chmod(hello_world_script_path, 0o755)

        agents_ref = {
            'monologue_agent': 'MonologueAgent',
            'codeact_agent': 'CodeActAgent',
            'codeact_swe_agent': 'CodeActSWEAgent',
            'planner_agent': 'PlannerAgent',
            'delegator_agent': 'DelegatorAgent',
            'dummy_agent': 'DummyAgent',
            'browsing_agent': 'BrowsingAgent',
        }

        if agent not in agents_ref:
            logging.error(f"Agent '{agent}' not found in agents_ref dictionary.")
            raise KeyError(f"Agent '{agent}' not found in agents_ref dictionary.")

        logging.info(f'Running agent: {agent}')
        logging.info(f'Task: {task}')
        logging.info(f"Workspace directory: {os.path.join(agent_dir, 'workspace')}")
        logging.info(
            f"Command: python3 {SCRIPT_DIR}/../../opendevin/core/main.py -d {os.path.join(agent_dir, 'workspace')} -c {agents_ref[agent]} -t {task} -m gpt-3.5-turbo"
        )
        logging.info(f'Environment: {os.environ}')

        process = subprocess.Popen(
            [
                'python3',
                f'{SCRIPT_DIR}/../../opendevin/core/main.py',
                '-d',
                f"{os.path.join(agent_dir, 'workspace')}",
                '-c',
                f'{agents_ref[agent]}',
                '-t',
                f'{task}',
                '-m',
                'gpt-3.5-turbo',
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
        )
        stdout, stderr = process.communicate()
        logging.info(f'Stdout: {stdout}')
        logging.error(f'Stderr: {stderr}')

        assert process.returncode == 0
        return os.path.join(agent_dir, 'workspace')

    return _run_test_case


def pytest_configure(config):
    """Configuration hook for pytest.

    Args:
        config: The pytest configuration object.
    """
    now = datetime.datetime.now()
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(f"test_results_{now.strftime('%Y%m%d_%H%M%S')}.log"),
            logging.StreamHandler(),
        ],
    )
