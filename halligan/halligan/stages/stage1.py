import halligan.prompts as Prompts
from halligan.agents import Agent
from halligan.utils.layout import Frame
from halligan.utils.constants import Stage
from halligan.utils.logger import Trace
from halligan.runtime.parser import parse_json_from_response
from halligan.runtime.schemas import validate_stage1
from halligan.runtime.errors import ParseError, ValidationError


stage = Stage.OBJECTIVE_IDENTIFICATION


@Trace.section("Objective Identification")
def objective_identification(agent: Agent, frames: list[Frame]) -> str:
    """
    Ask the agent to give a detailed visual description of each frame.
    Then, identify the relations between frames and infer the overall task objective.

    Updates:
        Frame.description
        Frame.relations
    
    Returns:
        objective (str): The inferred task objective.
    """
    # Prepare prompt
    prompt = Prompts.get(
        stage=stage,
        frames=len(frames)
    )
    print(prompt)

    # Request structured JSON from agent
    images = [frame.image for frame in frames]
    image_captions = [f"Frame {i}" for i in range(len(frames))]
    last_error: Exception | None = None
    for attempt in range(3):
        response, _ = agent(prompt, images, image_captions)
        try:
            data = parse_json_from_response(response)
            result = validate_stage1(data, frames=len(frames))

            for i, desc in enumerate(result.descriptions):
                frames[i].description = desc

            for rel in result.relations:
                frames[rel.src].relations[rel.dst] = rel.relationship

            agent.reset()
            return result.objective

        except (ParseError, ValidationError) as exc:
            last_error = exc
            prompt = (
                "Your previous output was invalid.\n"
                f"Error: {exc}\n\n"
                "Please output ONLY valid JSON that matches the required schema.\n"
                "Do not include markdown fences or any extra text."
            )

    agent.reset()
    raise last_error if last_error else RuntimeError("Stage 1 failed without a captured error")
