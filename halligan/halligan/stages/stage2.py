import halligan.prompts as Prompts
from halligan.agents import Agent
from halligan.runtime.errors import ParseError, ValidationError
from halligan.runtime.executor import apply_stage2_plan
from halligan.runtime.parser import parse_json_from_response
from halligan.runtime.schemas import validate_stage2
from halligan.utils.constants import Stage
from halligan.utils.layout import Frame, get_observation
from halligan.utils.logger import Trace

stage = Stage.STRUCTURE_ABSTRACTION


@Trace.section("Structure Abstraction")
def structure_abstraction(agent: Agent, frames: list[Frame], objective: str) -> None:
    """
    Instruct the agent to annotate interactable Frames and Elements.
    Frames can be further divided into subframes.
    The agent can segment specific Elements or extract a grid of evenly-sized Elements from Frames.

    Returns:
        None: all annotations are stored in the Frame instances (e.g., Frame.interactables).
    """
    # Prepare prompt
    _, images, image_captions, descriptions, relations, _ = get_observation(frames)
    prompt = Prompts.get(
        stage=stage,
        descriptions="\n".join(descriptions),
        relations="\n".join(relations),
        objective=objective,
    )
    print(prompt)

    last_error: Exception | None = None
    for attempt in range(3):
        response, _ = agent(prompt, images, image_captions)
        try:
            data = parse_json_from_response(response)
            plan = validate_stage2(data, frames=len(frames))
            apply_stage2_plan(frames, plan)
            agent.reset()
            return

        except (ParseError, ValidationError) as exc:
            last_error = exc
            prompt = (
                "Your previous output was invalid.\n"
                f"Error: {exc}\n\n"
                "Please output ONLY valid JSON that matches the required schema.\n"
                "Do not include markdown fences or any extra text."
            )

    agent.reset()
    raise last_error if last_error else RuntimeError("Stage 2 failed without a captured error")
