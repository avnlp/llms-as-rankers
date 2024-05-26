from datasets import load_dataset
from haystack_integrations.components.generators.llama_cpp import LlamaCppGenerator

from llms_as_rankers.llm_blender import LLMBlenderEvaluator


def construct_prompt(prompt=""):
    prompt_with_instruction = (
        """ Provide a comprehensive summary of the given text. """
        """The summary should cover all the key points and main ideas presented in the original text, """
        f"""while also condensing the information into a concise and easy-to-understand format.:\n{prompt}"""
    )
    # Format prompt to be compatible with solar-10.7b-instruct-v1.0
    formatted_prompt = f"""### User: {prompt_with_instruction}
    ### Assistant:"""

    return formatted_prompt


def generate_result(
    generator: LlamaCppGenerator,
    prompt: str = "",
) -> str:

    # Format prompt to be compatible with solar-10.7b-instruct-v1.0
    formatted_prompt = construct_prompt(prompt)

    # Generate text
    result = generator.run(
        formatted_prompt,
        generation_kwargs={"max_tokens": 128, "temperature": 0.2},
    )
    generated_answer = result["replies"][0]
    return generated_answer


model = "models/solar-10.7b-instruct-v1.0.Q4_K_M"
generator = LlamaCppGenerator(
    model=model,
    n_ctx=256,
)
generator.warm_up()

dataset = load_dataset("billsum", split="test")
dataset = dataset.to_pandas()
dataset.loc[:, "result"] = dataset.apply(
    lambda row: str(generate_result(generator=generator, prompt=row["text"])), axis=1
)
dataset.to_csv("output_openchat.csv", index=False)


evaluator = LLMBlenderEvaluator(preds=dataset["result"], labels=dataset["output"])
metrics = evaluator.compute_metrics()

print("BLEURT Score", metrics["bleurt"])
print("BARTSCORE Score", metrics["bartscore"])
print("BERTSCORE Score", metrics["bertscore"])