import agenthub.monologue_agent.utils.prompts as prompts
from agenthub.monologue_agent.response_parser import MonologueResponseParser
from agenthub.monologue_agent.utils.prompts import INITIAL_THOUGHTS
from opendevin.controller.agent import Agent
from opendevin.controller.state.state import State
from opendevin.core.config import config
from opendevin.core.exceptions import AgentNoInstructionError
from opendevin.core.schema import ActionType
from opendevin.events.action import (
    Action,
    AgentRecallAction,
    BrowseURLAction,
    CmdRunAction,
    FileReadAction,
    FileWriteAction,
    MessageAction,
    NullAction,
)
from opendevin.events.observation import (
    AgentRecallObservation,
    BrowserOutputObservation,
    CmdOutputObservation,
    FileReadObservation,
    NullObservation,
    Observation,
)
from opendevin.events.serialization.event import event_to_memory
from opendevin.llm.llm import LLM
from opendevin.memory.condenser import MemoryCondenser
from opendevin.runtime.tools import RuntimeTool

if config.agent.memory_enabled:
    from opendevin.memory.memory import LongTermMemory


class MonologueAgent(Agent):
    VERSION = '1.0'
    """
    The Monologue Agent utilizes long and short term memory to complete tasks.
    Long term memory is stored as a LongTermMemory object and the model uses it to search for examples from the past.
    Short term memory is stored as a Monologue object and the model can condense it as necessary.
    """

    _initialized = False
    initial_thoughts: list[dict[str, str]]
    memory: 'LongTermMemory | None'
    memory_condenser: MemoryCondenser
    runtime_tools: list[RuntimeTool] = [RuntimeTool.BROWSER]
    response_parser = MonologueResponseParser()

    def __init__(self, llm: LLM):
        """
        Initializes the Monologue Agent with an llm.

        Parameters:
        - llm (LLM): The llm to be used by this agent
        """
        super().__init__(llm)

    def _initialize(self, task: str):
        """
        Utilizes the INITIAL_THOUGHTS list to give the agent a context for its capabilities
        and how to navigate the WORKSPACE_MOUNT_PATH_IN_SANDBOX in `config` (e.g., /workspace by default).
        Short circuited to return when already initialized.
        Will execute again when called after reset.

        Parameters:
        - task: The initial goal statement provided by the user

        Raises:
        - AgentNoInstructionError: If task is not provided
        """

        if self._initialized:
            return

        if task is None or task == '':
            raise AgentNoInstructionError()

        self.initial_thoughts = []
        if config.agent.memory_enabled:
            self.memory = LongTermMemory()
        else:
            self.memory = None

        self.memory_condenser = MemoryCondenser()

        self._add_initial_thoughts(task)
        self._initialized = True

    def _add_initial_thoughts(self, task):
        previous_action = ''
        for thought in INITIAL_THOUGHTS:
            thought = thought.replace('$TASK', task)
            if previous_action != '':
                observation: Observation = NullObservation(content='')
                if previous_action in {ActionType.RUN, ActionType.PUSH}:
                    observation = CmdOutputObservation(
                        content=thought, command_id=0, command=''
                    )
                elif previous_action == ActionType.READ:
                    observation = FileReadObservation(content=thought, path='')
                elif previous_action == ActionType.RECALL:
                    observation = AgentRecallObservation(content=thought, memories=[])
                elif previous_action == ActionType.BROWSE:
                    observation = BrowserOutputObservation(
                        content=thought, url='', screenshot=''
                    )
                self.initial_thoughts.append(event_to_memory(observation))
                previous_action = ''
            else:
                action: Action = NullAction()
                if thought.startswith('RUN'):
                    command = thought.split('RUN ')[1]
                    action = CmdRunAction(command)
                    previous_action = ActionType.RUN
                elif thought.startswith('WRITE'):
                    parts = thought.split('WRITE ')[1].split(' > ')
                    path = parts[1]
                    content = parts[0]
                    action = FileWriteAction(path=path, content=content)
                elif thought.startswith('READ'):
                    path = thought.split('READ ')[1]
                    action = FileReadAction(path=path)
                    previous_action = ActionType.READ
                elif thought.startswith('RECALL'):
                    query = thought.split('RECALL ')[1]
                    action = AgentRecallAction(query=query)
                    previous_action = ActionType.RECALL
                elif thought.startswith('BROWSE'):
                    url = thought.split('BROWSE ')[1]
                    action = BrowseURLAction(url=url)
                    previous_action = ActionType.BROWSE
                else:
                    action = MessageAction(thought)
                self.initial_thoughts.append(event_to_memory(action))

    def step(self, state: State) -> Action:
        """
        Modifies the current state by adding the most recent actions and observations, then prompts the model to think about it's next action to take using monologue, memory, and hint.

        Parameters:
        - state (State): The current state based on previous steps taken

        Returns:
        - Action: The next action to take based on LLM response
        """

        goal = state.get_current_user_intent()
        self._initialize(goal)

        recent_events: list[dict[str, str]] = []

        # add the events from state.history
        for event in state.history.get_events():
            recent_events.append(event_to_memory(event))

        # add the last messages to long term memory
        if self.memory is not None:
            last_action = state.history.get_last_action()
            last_observation = state.history.get_last_observation()

            # this should still work
            # we will need to do this differently: find out if there really is an action or an observation in this step
            if last_action:
                self.memory.add_event(event_to_memory(last_action))
            if last_observation:
                self.memory.add_event(event_to_memory(last_observation))

        # the action prompt with initial thoughts and recent events
        prompt = prompts.get_request_action_prompt(
            goal, self.initial_thoughts, recent_events
        )

        messages: list[dict[str, str]] = [
            {'role': 'user', 'content': prompt},
        ]

        # format all as a single message, a monologue
        resp = self.llm.completion(messages=messages)

        action = self.response_parser.parse(resp)
        self.latest_action = action
        return action

    def search_memory(self, query: str) -> list[str]:
        """
        Uses VectorIndexRetriever to find related memories within the long term memory.
        Uses search to produce top 10 results.

        Parameters:
        - The query that we want to find related memories for

        Returns:
        - A list of top 10 text results that matched the query
        """
        if self.memory is None:
            return []
        return self.memory.search(query)

    def reset(self) -> None:
        super().reset()

        # Reset the initial monologue and memory
        self._initialized = False
