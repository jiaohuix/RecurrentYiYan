import gradio as gr

from recurrentyiyan import RecurrentYiYan

from human_simulator import Human
from sentence_transformers import SentenceTransformer
from utils import get_init, parse_instructions
import re

# from urllib.parse import quote_plus
# from pymongo import MongoClient

# uri = "mongodb://%s:%s@%s" % (quote_plus("xxx"),
#                               quote_plus("xxx"), "localhost")
# client = MongoClient(uri, maxPoolSize=None)
# db = client.recurrentGPT_db
# log = db.log

_CACHE = {}

embed_name = "GanymedeNil/text2vec-large-chinese"
embed_name = "shibing624/text2vec-base-chinese"
# Build the semantic search model
embedder = SentenceTransformer(embed_name)

def init_prompt(novel_type, description):
    if description == "":
        description = ""
    else:
        description = " about " + description
    return f"""
请写一本关于{novel_type}的{description}中文小说，大约有50个章节。准确地按照下面的格式来写：
先为小说起一个有趣且容易记忆的书名。 
接下来，为第1章写一个剧情Outline。Outline应描述小说的背景和开端。
根据你的Outline，写出小说的前[3]段落及其说明。用小说的风格来写，慢慢地设置场景。
再写一个摘要，抓住[3]个段落的关键信息。
最后，写出[3]个不同的指令，说明接下来要写什么，每个指令包含大约五句话。每条指令都应提出一个可能的、有趣的故事的延续。
输出格式应遵循以下准则，前缀标题用英文显示： 
Name： <小说的名称>  
Outline: <第1章的大纲> 
Paragraph 1: <第1段的内容> 
Paragraph 2: <第2段的内容> 
Paragraph 3: <第3段的内容> 
Summary： <摘要内容>
Instruction 1: <指令1的内容>
Instruction 2: <指令2的内容>
Instruction 3: <指令3的内容>
确保精确并严格遵循输出格式，不要多写漏写。

确保准确无误，严格遵循输出格式。
"""

def init(novel_type, description, request: gr.Request):
    if novel_type == "":
        novel_type = "Science Fiction"
    global _CACHE
    cookie = request.headers['cookie']
    cookie = cookie.split('; _gat_gtag')[0]
    # prepare first init
    init_paragraphs = get_init(text=init_prompt(novel_type,description))
    # print(init_paragraphs)
    start_input_to_human = {
        'output_paragraph': init_paragraphs['Paragraph 3'],
        'input_paragraph': '\n\n'.join([init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']]),
        'output_memory': init_paragraphs['Summary'],
        "output_instruction": [init_paragraphs['Instruction 1'], init_paragraphs['Instruction 2'], init_paragraphs['Instruction 3']]
    }

    _CACHE[cookie] = {"start_input_to_human": start_input_to_human,
                      "init_paragraphs": init_paragraphs}
    written_paras = f"""Title: {init_paragraphs['name']}

Outline: {init_paragraphs['Outline']}

Paragraphs:

{start_input_to_human['input_paragraph']}"""
    long_memory = parse_instructions([init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']])
    # short memory, long memory, current written paragraphs, 3 next instructions
    return start_input_to_human['output_memory'], long_memory, written_paras, init_paragraphs['Instruction 1'], init_paragraphs['Instruction 2'], init_paragraphs['Instruction 3']

def step(short_memory, long_memory, instruction1, instruction2, instruction3, current_paras, request: gr.Request, ):
    if current_paras == "":
        return "", "", "", "", "", ""
    global _CACHE
    # print(list(_CACHE.keys()))
    # print(request.headers.get('cookie'))
    import time
    cookie = str(time.time())
    # cookie = request.headers['cookie']
    # cookie = cookie.split('; _gat_gtag')[0]
    cache = _CACHE[cookie]

    if "writer" not in cache:
        start_input_to_human = cache["start_input_to_human"]
        start_input_to_human['output_instruction'] = [
            instruction1, instruction2, instruction3]
        init_paragraphs = cache["init_paragraphs"]
        human = Human(input=start_input_to_human,
                      memory=None, embedder=embedder)
        human.step()
        start_short_memory = init_paragraphs['Summary']
        writer_start_input = human.output

        # Init writerGPT
        writer = RecurrentYiYan(input=writer_start_input, short_memory=start_short_memory, long_memory=[
            init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']], memory_index=None, embedder=embedder)
        cache["writer"] = writer
        cache["human"] = human
        writer.step()
    else:
        human = cache["human"]
        writer = cache["writer"]
        output = writer.output
        output['output_memory'] = short_memory
        output['output_instruction'] = [
            instruction1, instruction2, instruction3]
        human.input = output
        human.step()
        writer.input = human.output
        writer.step()

    long_memory = [[v] for v in writer.long_memory]
    # short memory, long memory, current written paragraphs, 3 next instructions
    return writer.output['output_memory'], long_memory, current_paras + '\n\n' + writer.output['input_paragraph'], human.output['output_instruction'], *writer.output['output_instruction']


def controled_step(short_memory, long_memory, selected_instruction, current_paras, request: gr.Request, ):
    if current_paras == "":
        return "", "", "", "", "", ""
    global _CACHE
    print(list(_CACHE.keys()))
    # print(request.headers.get('cookie'))
    cookie = request.headers['cookie']
    cookie = cookie.split('; _gat_gtag')[0]
    cache = _CACHE[cookie]
    if "writer" not in cache:
        start_input_to_human = cache["start_input_to_human"]
        start_input_to_human['output_instruction'] = selected_instruction
        init_paragraphs = cache["init_paragraphs"]
        human = Human(input=start_input_to_human,
                      memory=None, embedder=embedder)
        # human.step_with_edit()
        human.step()
        start_short_memory = init_paragraphs['Summary']
        writer_start_input = human.output

        # Init writerGPT
        writer = RecurrentYiYan(input=writer_start_input, short_memory=start_short_memory, long_memory=[
            init_paragraphs['Paragraph 1'], init_paragraphs['Paragraph 2']], memory_index=None, embedder=embedder)
        cache["writer"] = writer
        cache["human"] = human
        writer.step()
    else:
        human = cache["human"]
        writer = cache["writer"]
        output = writer.output
        output['output_memory'] = short_memory
        output['output_instruction'] = selected_instruction
        human.input = output
        human.step_with_edit()
        writer.input = human.output
        writer.step()

    # short memory, long memory, current written paragraphs, 3 next instructions
    return writer.output['output_memory'], parse_instructions(writer.long_memory), current_paras + '\n\n' + writer.output['input_paragraph'], *writer.output['output_instruction']


# SelectData is a subclass of EventData
def on_select(instruction1, instruction2, instruction3, evt: gr.SelectData):
    selected_plan = int(evt.value.replace("Instruction ", ""))
    selected_plan = [instruction1, instruction2, instruction3][selected_plan-1]
    return selected_plan


with gr.Blocks(title="RecurrentYiYan", css="footer {visibility: hidden}", theme="default") as demo:
    gr.Markdown(
        """
    # RecurrentYiYan
        Recurrent YiYan: Interactively use YiYan to generate Chinese long text
    """)
    with gr.Tab("Auto-Generation"):
        with gr.Row():
            with gr.Column():
                with gr.Box():
                    with gr.Row():
                        with gr.Column(scale=1, min_width=200):
                            novel_type = gr.Textbox(
                                label="Novel Type", placeholder="e.g. science fiction")
                        with gr.Column(scale=2, min_width=400):
                            description = gr.Textbox(label="Description")
                btn_init = gr.Button(
                    "Init Novel Generation", variant="primary")
                gr.Examples(["科幻", "浪漫", "悬疑", "幻想",
                            "历史", "恐怖", "惊悚", "西部"], inputs=[novel_type])
                written_paras = gr.Textbox(
                    label="Written Paragraphs (editable)", max_lines=21, lines=21)
            with gr.Column():
                with gr.Box():
                    gr.Markdown("### Memory Module\n")
                    short_memory = gr.Textbox(
                        label="Short-Term Memory (editable)", max_lines=3, lines=3)
                    long_memory = gr.Textbox(
                        label="Long-Term Memory (editable)", max_lines=6, lines=6)
                    # long_memory = gr.Dataframe(
                    #     # label="Long-Term Memory (editable)",
                    #     headers=["Long-Term Memory (editable)"],
                    #     datatype=["str"],
                    #     row_count=3,
                    #     max_rows=3,
                    #     col_count=(1, "fixed"),
                    #     type="array",
                    # )
                with gr.Box():
                    gr.Markdown("### Instruction Module\n")
                    with gr.Row():
                        instruction1 = gr.Textbox(
                            label="Instruction 1 (editable)", max_lines=4, lines=4)
                        instruction2 = gr.Textbox(
                            label="Instruction 2 (editable)", max_lines=4, lines=4)
                        instruction3 = gr.Textbox(
                            label="Instruction 3 (editable)", max_lines=4, lines=4)
                    selected_plan = gr.Textbox(
                        label="Revised Instruction (from last step)", max_lines=2, lines=2)

                btn_step = gr.Button("Next Step", variant="primary")

        btn_init.click(init, inputs=[novel_type, description], outputs=[
            short_memory, long_memory, written_paras, instruction1, instruction2, instruction3])
        btn_step.click(step, inputs=[short_memory, long_memory, instruction1, instruction2, instruction3, written_paras], outputs=[
            short_memory, long_memory, written_paras, selected_plan, instruction1, instruction2, instruction3])

    with gr.Tab("Human-in-the-Loop"):
        with gr.Row():
            with gr.Column():
                with gr.Box():
                    with gr.Row():
                        with gr.Column(scale=1, min_width=200):
                            novel_type = gr.Textbox(
                                label="Novel Type", placeholder="e.g. science fiction")
                        with gr.Column(scale=2, min_width=400):
                            description = gr.Textbox(label="Description")
                btn_init = gr.Button(
                    "Init Novel Generation", variant="primary")
                gr.Examples(["科幻", "浪漫", "悬疑", "幻想",
                            "历史", "恐怖", "惊悚", "西部"], inputs=[novel_type])
                written_paras = gr.Textbox(
                    label="Written Paragraphs (editable)", max_lines=23, lines=23)
            with gr.Column():
                with gr.Box():
                    gr.Markdown("### Memory Module\n")
                    short_memory = gr.Textbox(
                        label="Short-Term Memory (editable)", max_lines=3, lines=3)
                    long_memory = gr.Textbox(
                        label="Long-Term Memory (editable)", max_lines=6, lines=6)
                with gr.Box():
                    gr.Markdown("### Instruction Module\n")
                    with gr.Row():
                        instruction1 = gr.Textbox(
                            label="Instruction 1", max_lines=3, lines=3, interactive=False)
                        instruction2 = gr.Textbox(
                            label="Instruction 2", max_lines=3, lines=3, interactive=False)
                        instruction3 = gr.Textbox(
                            label="Instruction 3", max_lines=3, lines=3, interactive=False)
                    with gr.Row():
                        with gr.Column(scale=1, min_width=100):
                            selected_plan = gr.Radio(["Instruction 1", "Instruction 2", "Instruction 3"], label="Instruction Selection",)
                                                    #  info="Select the instruction you want to revise and use for the next step generation.")
                        with gr.Column(scale=3, min_width=300):
                            selected_instruction = gr.Textbox(
                                label="Selected Instruction (editable)", max_lines=5, lines=5)

                btn_step = gr.Button("Next Step", variant="primary")

        btn_init.click(init, inputs=[novel_type, description], outputs=[
            short_memory, long_memory, written_paras, instruction1, instruction2, instruction3])
        btn_step.click(controled_step, inputs=[short_memory, long_memory, selected_instruction, written_paras], outputs=[
            short_memory, long_memory, written_paras, instruction1, instruction2, instruction3])
        selected_plan.select(on_select, inputs=[
                             instruction1, instruction2, instruction3], outputs=[selected_instruction])

    demo.queue(concurrency_count=1)

if __name__ == "__main__":
    demo.launch(server_port=8005, share=True,
                server_name="127.0.0.1", show_api=False)