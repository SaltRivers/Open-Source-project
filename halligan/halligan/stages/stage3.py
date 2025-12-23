import halligan.prompts as Prompts
import halligan.utils.examples as Examples
from halligan.agents import Agent
from halligan.runtime.errors import ParseError, ToolError, ValidationError
from halligan.runtime.executor import execute_stage3_program
from halligan.runtime.parser import parse_json_from_response
from halligan.runtime.registry import build_default_registry
from halligan.runtime.schemas import validate_stage3
from halligan.utils.constants import InteractableElement, Stage
from halligan.utils.layout import Frame, get_observation
from halligan.utils.logger import Trace

stage = Stage.SOLUTION_COMPOSITION


@Trace.section("Solution Composition")
def solution_composition(agent: Agent, frames: list[Frame], objective: str) -> None:
    """
    Agent composes a Python executable solution using vision and action tools.
    """
    examples = []
    all_frames, images, image_captions, descriptions, relations, interactable_types = get_observation(frames)

    for interactable_type in interactable_types:
        # Prepare in-context learning examples
        if interactable_type == InteractableElement.NEXT.name:
            continue
        else:
            examples.append(Examples.get(interactable_type))

    # Tools exposed to the JSON program (functions only)
    registry = build_default_registry()
    action_tools = "\n".join(
        [
            "- click(target)",
            "- get_all_choices(prev_arrow, next_arrow, observe)",
            "- drag(start, end)",
            "- slide_x(handle, direction, observe_frame)",
            "- slide_y(handle, direction, observe_frame)",
            "- explore(grid)",
            "- select(choice)",
            "- point(to)",
            "- enter(field, text)",
            "- draw(path)",
        ]
    )
    vision_tools = "\n".join(
        [
            "- mark(images, object)",
            "- focus(image, description)",
            "- ask(images, question, answer_type)",
            "- compare(images, task_objective, reference)",
            "- rank(images, task_objective)",
            "- match(e1, e2)",
        ]
    )

    # Prepare prompt
    prompt = Prompts.get(
        stage=stage,
        descriptions="\n".join(descriptions),
        relations="\n".join(relations),
        objective=objective,
        examples="\n\n".join(examples),
        action_tools=action_tools,
        vision_tools=vision_tools,
    )
    print(prompt)

    # Request JSON program from agent and execute it safely
    feedback: Exception | None = None
    for _ in range(4):
        try:
            # Keep agent history isolated from tool-calls inside vision_tools
            agent.reset()

            response, _ = agent(prompt, images, image_captions)
            data = parse_json_from_response(response)
            program = validate_stage3(data)

            # Vision tools require an injected agent instance.
            agent.reset()
            vision_tools.set_agent(agent)
            execute_stage3_program(all_frames, program, registry=registry)
            agent.reset()
            return

        except (ParseError, ValidationError, ToolError, Exception) as exc:
            feedback = exc
            prompt = (
                "Your previous output failed to parse/validate/execute.\n"
                f"Error: {exc}\n\n"
                "Please output ONLY valid JSON that matches the required schema.\n"
                "Do not include markdown fences or any extra text."
            )

    agent.reset()
    raise feedback if feedback else RuntimeError("Stage 3 failed without a captured error")
