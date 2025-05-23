from pathlib import Path

from patchwork.common.client.llm.aio import AioLlmClient
from patchwork.common.multiturn_strategy.agentic_strategy_v2 import (
    AgentConfig,
    AgenticStrategyV2,
)
from patchwork.common.tools.git_tool import GitTool
from patchwork.common.tools.github_tool import GitHubTool
from patchwork.common.utils.utils import mustache_render
from patchwork.step import Step
from patchwork.steps.GitHubAgent.typed import GitHubAgentInputs, GitHubAgentOutputs


class GitHubAgent(Step, input_class=GitHubAgentInputs, output_class=GitHubAgentOutputs):
    def __init__(self, inputs):
        super().__init__(inputs)
        base_path = inputs.get("base_path", str(Path.cwd()))
        data = inputs.get("prompt_value", {})
        task = mustache_render(inputs["task"], data)
        self.agentic_strategy = AgenticStrategyV2(
            model="gemini-2.0-flash",
            llm_client=AioLlmClient.create_aio_client(inputs),
            template_data=dict(),
            system_prompt_template="""\
Please summarise the conversation given and provide the result in the structure that is asked of you.
""",
            user_prompt_template=f"""\
Please help me with the following task using the GitHub CLI. You should not do anything extra.
Please take note of any requirements to the data required to fetch.

{task}
""",
            agent_configs=[
                AgentConfig(
                    name="Assistant",
                    model="gemini-2.0-flash",
                    tool_set=dict(
                        github_tool=GitHubTool(base_path, inputs["github_api_key"]),
                        git_tool=GitTool(base_path),
                    ),
                    system_prompt="""\
You are a senior software developer helping the program manager to obtain some data from GitHub.
You can access github through the `gh` CLI app through the `github_tool`, and `git` through the `git_tool`.
Your `gh` app has already been authenticated.
""",
                )
            ],
            example_json=inputs.get(
                "example_json", '{"summary_of_actions": "1. Retrieved the list of repositories. 2. ..."}'
            ),
        )

    def run(self) -> dict:
        result = self.agentic_strategy.execute(limit=10)
        return {**result, **self.agentic_strategy.usage()}
