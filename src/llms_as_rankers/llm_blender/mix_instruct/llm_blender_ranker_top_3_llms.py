from datasets import load_dataset
from haystack import Pipeline
from haystack.components.builders import PromptBuilder
from haystack_integrations.components.generators.llama_cpp import LlamaCppGenerator

from llms_as_rankers.llm_blender import LLMBlenderEvaluator, LLMBlenderRanker

dataset = load_dataset("llm-blender/mix-instruct", split="validation")

openchat_prompt_template = """GPT4 Correct User: {{ instruction }}
{{ prompt }}GPT4 Correct Assistant:"""

openhermes_prompt_template = """<|im_start|>system
{{ instruction }}<|im_end|>
<|im_start|>user
{{ prompt }}<|im_end|>
<|im_start|>assistant"""

solar_prompt_template = """### User:  {{ instruction }}
{{ prompt }} ### Assistant:"""

openchat_prompt_builder = PromptBuilder(template=openchat_prompt_template)
openhermes_prompt_builder = PromptBuilder(template=openhermes_prompt_template)
solar_prompt_builder = PromptBuilder(template=solar_prompt_template)

openchat_model = LlamaCppGenerator(
    model="models/openchat-3.5-0106.Q4_K_M.gguf", n_ctx=256, generation_kwargs={"max_tokens": 128, "temperature": 0.2}
)
openhermes_model = LlamaCppGenerator(
    model="models/openhermes-2.5-mistral-7b.Q4_K_M.gguf",
    n_ctx=256,
    generation_kwargs={"max_tokens": 128, "temperature": 0.2},
)
solar_model = LlamaCppGenerator(
    model="models/solar-7b-Q4_K_M.gguf", n_ctx=256, generation_kwargs={"max_tokens": 128, "temperature": 0.2}
)

llm_blender_ranker = LLMBlenderRanker(model="llm-blender/PairRM", device="cpu")

blender_pipeline = Pipeline()

blender_pipeline.add_component(instance=openchat_prompt_builder, name="openchat_prompt_builder")
blender_pipeline.add_component(instance=openchat_model, name="openchat_model")

blender_pipeline.add_component(instance=openhermes_prompt_builder, name="openhermes_prompt_builder")
blender_pipeline.add_component(instance=openhermes_model, name="openhermes_model")

blender_pipeline.add_component(instance=solar_prompt_builder, name="solar_prompt_builder")
blender_pipeline.add_component(instance=solar_model, name="solar_model")

blender_pipeline.add_component(instance=llm_blender_ranker, name="llm_blender_ranker")

blender_pipeline.connect("openchat_prompt_builder", "openchat_model")
blender_pipeline.connect("openhermes_prompt_builder", "openhermes_model")
blender_pipeline.connect("solar_prompt_builder", "solar_model")
blender_pipeline.connect("qwen_prompt_builder", "qwen_model")
blender_pipeline.connect("mistral_prompt_builder", "mistral_model")

blender_pipeline.connect("openchat_model", "llm_blender_ranker")
blender_pipeline.connect("openhermes_model", "llm_blender_ranker")
blender_pipeline.connect("solar_model", "llm_blender_ranker")
blender_pipeline.connect("qwen_model", "llm_blender_ranker")
blender_pipeline.connect("mistral_model", "llm_blender_ranker")

generated_answers_labels = []
for row in dataset:
    instruction = row["instruction"]
    prompt = row["input"]
    label = row["output"]
    output = blender_pipeline.run(
        {
            {"openchat_prompt_builder": {"instruction": instruction, "prompt": prompt}},
            {"openhermes_prompt_builder": {"instruction": instruction, "prompt": prompt}},
            {"solar_prompt_builder": {"instruction": instruction, "prompt": prompt}},
        }
    )
    generated_answers_labels.append((output["answers"], label))

preds = []
labels = []
for ranked_answers, label in generated_answers_labels:
    # Use top ranked output as the answer
    preds.append(ranked_answers[0].data)
    labels.append(label)

evaluator = LLMBlenderEvaluator(preds=preds, labels=labels)
metrics = evaluator.compute_metrics()

print("BLEURT Score", metrics["bleurt"])
print("BARTSCORE Score", metrics["bartscore"])
print("BERTSCORE Score", metrics["bertscore"])
